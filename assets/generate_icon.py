#!/usr/bin/env python3
"""Convert the DreamXcast neon launcher artwork into PS5 sce_sys/icon0.png."""
from pathlib import Path
from PIL import Image
import argparse
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "dreamxcast-neon.avif"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if not SRC.is_file() or SRC.stat().st_size < 3000:
        raise RuntimeError("Missing or invalid DreamXcast neon icon asset: " + str(SRC))
    dec = shutil.which("avifdec")
    if not dec:
        raise RuntimeError("Missing libavif-bin (avifdec); install before building.")
    with tempfile.TemporaryDirectory() as temp:
        intermediate = Path(temp) / "decoded.png"
        subprocess.run([dec, str(SRC), str(intermediate)], check=True)
        with Image.open(intermediate) as raw:
            if raw.width < 256 or raw.height < 256:
                raise RuntimeError("DreamXcast artwork too small")
            im = raw.convert("RGB").resize((512, 512), Image.Resampling.LANCZOS)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            im.save(args.output, format="PNG", optimize=True)
    with Image.open(args.output) as final:
        assert final.format == "PNG" and final.size == (512, 512) and final.mode == "RGB"
    print("PS5 DreamXcast home-screen icon:", args.output)

if __name__ == "__main__":
    main()
