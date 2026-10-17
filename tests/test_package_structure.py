#!/usr/bin/env python3
"""Fast regression check: title ID ZIP name != install root directory."""
import json
import os
import struct
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_package import verify

with tempfile.TemporaryDirectory() as temp:
    tmp = Path(temp)
    app = {
        "titleId": "PPSA99765",
        "installFolder": "PS5DreamcastX",
        "name": "DreamXcast",
    }
    manifest = tmp / "app.json"
    manifest.write_text(json.dumps(app))

    def make(package_root):
        package = tmp / "PPSA99765.zip"
        prefix = package_root + "/"
        with ZipFile(package, "w", ZIP_DEFLATED) as z:
            z.writestr(prefix + "eboot.bin", struct.pack("<I", 0x1D3D154F) + os.urandom(125_000))
            z.writestr(prefix + "sce_sys/param.json", json.dumps({
                "titleId": "PPSA99765", "localizedParameters": {"en-US": {"titleName": "DreamXcast"}}
            }))
            z.writestr(prefix + "sce_sys/icon0.png", b"\x89PNG\r\n\x1a\n")
            z.writestr(prefix + "sce_module/libc.prx", b"prx")
            z.writestr(prefix + "LEGAL.txt", b"credits")
        return package

    good = make("PS5DreamcastX")
    verify(good, manifest)
    wrong = make("PPSA99765")
    try:
        verify(wrong, manifest)
    except AssertionError:
        print("PASS: old PPSA99765/ ZIP folder correctly rejected")
    else:
        raise AssertionError("Incorrect install root passed ZIP validation")
