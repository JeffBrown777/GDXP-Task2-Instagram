#!/usr/bin/env python3
import base64, json
from pathlib import Path
from PIL import Image, ImageOps

manifest=json.loads(Path("assets_b64/manifest.json").read_text(encoding="utf-8"))
png_dir=Path("png"); png_dir.mkdir(exist_ok=True)
ig_dir=Path("instagram_media"); ig_dir.mkdir(exist_ok=True)

for item in manifest:
    source=png_dir/item["filename"]
    if not source.exists():
        data="".join((Path("assets_b64")/item["dir"]/c).read_text(encoding="ascii").strip() for c in item["chunks"])
        source.write_bytes(base64.b64decode(data))
        print(f"reconstructed {source}")

    publish_name=Path(item["filename"]).with_suffix(".jpg").name
    publish_path=ig_dir/publish_name
    rebuild=(not publish_path.exists()) or publish_path.stat().st_mtime < source.stat().st_mtime
    if rebuild:
        with Image.open(source) as im:
            im=ImageOps.exif_transpose(im)
            if im.mode in ("RGBA","LA") or (im.mode=="P" and "transparency" in im.info):
                rgba=im.convert("RGBA")
                bg=Image.new("RGBA", rgba.size, (255,255,255,255))
                bg.alpha_composite(rgba)
                rgb=bg.convert("RGB")
            else:
                rgb=im.convert("RGB")
            if rgb.width > 1440:
                new_height = round(rgb.height * 1440 / rgb.width)
                rgb = rgb.resize((1440, new_height), Image.Resampling.LANCZOS)
            ratio = rgb.width / rgb.height
            if ratio < 0.8 or ratio > 1.91:
                raise SystemExit(f"Instagram transport aspect ratio out of range for {source}")
            rgb.save(publish_path, format="JPEG", quality=95, subsampling=0, optimize=True)
        print(f"created Instagram JPEG transport asset {publish_path} from approved source {source}")
