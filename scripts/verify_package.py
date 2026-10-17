#!/usr/bin/env python3
"""Validate the installable PS5DreamcastX ZIP against app.json.

The ZIP's *filename* remains PPSA99765.zip (title ID), while its
single top-level *folder* is PS5DreamcastX/. The previous CI accidentally
treated these as the same string and rejected a fully compiled PS5 SELF.
"""
import argparse
import json
import hashlib
import struct
from pathlib import Path
from zipfile import ZipFile


def verify(package: Path, manifest: Path) -> None:
    app = json.loads(manifest.read_text(encoding="utf-8"))
    title_id = app["titleId"]
    root = app["installFolder"].strip("/")
    assert root and "/" not in root and root not in (".", "..")
    assert package.name == title_id + ".zip", (package.name, title_id)
    assert package.is_file() and package.stat().st_size > 100_000
    required = {
        "eboot.bin",
        "sce_sys/param.json",
        "sce_sys/icon0.png",
        "sce_module/libc.prx",
        "LEGAL.txt",
    }
    prefix = root + "/"
    with ZipFile(package) as archive:
        assert archive.testzip() is None, "Corrupt ZIP member"
        files = {name for name in archive.namelist() if not name.endswith("/")}
        assert all(name.startswith(prefix) for name in files), "ZIP contains files outside the install root"
        assert {prefix + name for name in required} <= files, "Required PS5 files missing"
        executable = archive.getinfo(prefix + "eboot.bin")
        assert executable.file_size > 100_000, "eboot.bin too small"
        with archive.open(prefix + "eboot.bin") as eboot:
            assert eboot.read(4) == struct.pack("<I", 0x1D3D154F), "Not a signed PS5 SELF"
        icon = archive.read(prefix + "sce_sys/icon0.png")
        assert icon[:8] == b"\x89PNG\r\n\x1a\n", "Invalid PS5 launcher icon PNG"
        expected = manifest.parent / "build" / "icon0.png"
        if expected.exists():
            assert hashlib.sha256(icon).digest() == hashlib.sha256(expected.read_bytes()).digest(), "Stale or incorrect PS5 icon0.png"
        param = json.loads(archive.read(prefix + "sce_sys/param.json"))
        assert param["titleId"] == title_id, (param["titleId"], title_id)
        if "contentVersion" in app:
            assert param["contentVersion"] == app["contentVersion"], "Outdated package content version"
        assert param["localizedParameters"]["en-US"]["titleName"] == app["name"]
    print(f"PASS: signed PS5 package {package.name}, installed to {root}/, Title ID {title_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] / "app.json")
    args = parser.parse_args()
    verify(args.zip_path, args.manifest)
