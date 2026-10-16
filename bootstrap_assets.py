#!/usr/bin/env python3
import base64, json
from pathlib import Path

manifest=json.loads(Path("assets_b64/manifest.json").read_text(encoding="utf-8"))
outdir=Path("png"); outdir.mkdir(exist_ok=True)
for item in manifest:
    target=outdir/item["filename"]
    if target.exists():
        continue
    data="".join((Path("assets_b64")/item["dir"]/c).read_text(encoding="ascii").strip() for c in item["chunks"])
    target.write_bytes(base64.b64decode(data))
    print(f"reconstructed {target}")
