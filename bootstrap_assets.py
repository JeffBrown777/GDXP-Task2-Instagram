#!/usr/bin/env python3
import base64
import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(".")
ASSETS_DIR = ROOT / "assets_b64"
PNG_DIR = ROOT / "png"
IG_DIR = ROOT / "instagram_media"
MANIFEST_PATH = ASSETS_DIR / "manifest.json"
APPROVED_PATH = ROOT / "approved_source_assets.json"

PNG_DIR.mkdir(exist_ok=True)
IG_DIR.mkdir(exist_ok=True)

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
approved = json.loads(APPROVED_PATH.read_text(encoding="utf-8"))

if not isinstance(manifest, list) or not manifest:
    raise SystemExit("Task 2 asset manifest must be a non-empty list")
if not isinstance(approved, dict) or not approved:
    raise SystemExit("Task 2 approved source controls must be a non-empty object")

manifest_names = [item.get("filename") for item in manifest if isinstance(item, dict)]
if len(manifest_names) != len(manifest) or any(not x for x in manifest_names):
    raise SystemExit("Task 2 asset manifest contains an invalid filename entry")
if len(set(manifest_names)) != len(manifest_names):
    raise SystemExit("Task 2 asset manifest contains duplicate filenames")
if set(manifest_names) != set(approved):
    raise SystemExit("Task 2 encoded asset manifest does not exactly match approved source controls")

for item in manifest:
    filename = item["filename"]
    source_control = approved.get(filename) or {}
    expected_source_sha = str(source_control.get("source_sha256") or "").strip().lower()
    if len(expected_source_sha) != 64:
        raise SystemExit(f"Approved source SHA-256 missing/invalid: {filename}")

    asset_dir = str(item.get("dir") or "").strip()
    chunks = item.get("chunks")
    if not asset_dir or not isinstance(chunks, list) or not chunks or len(set(chunks)) != len(chunks):
        raise SystemExit(f"Encoded source definition invalid: {filename}")

    encoded_parts = []
    for chunk_name in chunks:
        if not isinstance(chunk_name, str) or not chunk_name:
            raise SystemExit(f"Encoded source chunk name invalid: {filename}")
        chunk_path = ASSETS_DIR / asset_dir / chunk_name
        if not chunk_path.is_file():
            raise SystemExit(f"Encoded source chunk missing: {chunk_path}")
        encoded_parts.append(chunk_path.read_text(encoding="ascii").strip())

    try:
        source_bytes = base64.b64decode("".join(encoded_parts), validate=True)
    except Exception as exc:
        raise SystemExit(f"Encoded source base64 invalid for {filename}: {exc}")

    source_sha = hashlib.sha256(source_bytes).hexdigest()
    if source_sha != expected_source_sha:
        raise SystemExit(f"Encoded source SHA-256 does not match approved source: {filename}")

    source = PNG_DIR / filename
    existing_sha = hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None
    if existing_sha != expected_source_sha:
        tmp_source = source.with_name(source.name + ".tmp")
        tmp_source.write_bytes(source_bytes)
        if hashlib.sha256(tmp_source.read_bytes()).hexdigest() != expected_source_sha:
            tmp_source.unlink(missing_ok=True)
            raise SystemExit(f"Reconstructed source verification failed: {filename}")
        os.replace(tmp_source, source)
        print(f"reconstructed verified approved source {source}")

    if source.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"Approved source PNG signature invalid: {source}")

    publish_name = Path(filename).with_suffix(".jpg").name
    publish_path = IG_DIR / publish_name
    tmp_publish = publish_path.with_name(publish_path.name + ".tmp")

    with Image.open(source) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            rgba = im.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            bg.alpha_composite(rgba)
            rgb = bg.convert("RGB")
        else:
            rgb = im.convert("RGB")

        if rgb.width > 1440:
            new_height = round(rgb.height * 1440 / rgb.width)
            rgb = rgb.resize((1440, new_height), Image.Resampling.LANCZOS)

        ratio = rgb.width / rgb.height
        if ratio < 0.8 or ratio > 1.91:
            raise SystemExit(f"Instagram transport aspect ratio out of range for {source}")

        rgb.save(tmp_publish, format="JPEG", quality=95, subsampling=0, optimize=True)

    transport_bytes = tmp_publish.read_bytes()
    if not transport_bytes.startswith(b"\xff\xd8\xff"):
        tmp_publish.unlink(missing_ok=True)
        raise SystemExit(f"Generated transport JPEG signature invalid: {publish_name}")

    with Image.open(tmp_publish) as verify_im:
        verify_im.verify()

    os.replace(tmp_publish, publish_path)
    print(
        f"created verified Instagram JPEG transport asset {publish_path} "
        f"from approved source {source}"
    )
