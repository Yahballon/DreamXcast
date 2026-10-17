#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
test -s build/flycast/shell/ps5/dreamcastx_shelf.inc || python3 scripts/prepare.py
python3 scripts/verify.py
: "${PS5_VULKAN_DIR:?Set PS5_VULKAN_DIR}"
: "${PS5_PAYLOAD_SDK:?Set PS5_PAYLOAD_SDK}"
mkdir -p dist
bash build/flycast/shell/ps5/build.sh "$root/dist"
test -s dist/PS5DreamcastX/eboot.bin
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from hashlib import sha256
import json,struct
root=Path("dist/PS5DreamcastX")
exe=root/"eboot.bin"
assert exe.is_file() and exe.stat().st_size>100000
assert exe.read_bytes()[:4]==struct.pack("<I",0x1D3D154F), "Not a signed SELF executable"
meta=json.loads((root/"sce_sys/param.json").read_text())
assert meta["titleId"]=="PPSA99765"
assert meta["localizedParameters"]["en-US"]["titleName"]=="DreamXcast"
for p in ("sce_sys/icon0.png","sce_module/libc.prx","LEGAL.txt"):
    assert (root/p).is_file(),p
out=Path("dist/PPSA99765.zip")
with ZipFile(out,"w",ZIP_DEFLATED) as z:
    for p in sorted(root.rglob("*")):
        if p.is_file():
            z.write(p,p.relative_to(root.parent))
with ZipFile(out) as z:
    assert z.testzip() is None
    assert "PS5DreamcastX/eboot.bin" in z.namelist()
print("Verified signed native PS5 ZIP:",out,"sha256",sha256(out.read_bytes()).hexdigest())
PY
