#!/usr/bin/env python3
import json, os, sys, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

PHX = ZoneInfo("America/Phoenix")
QUEUE_PATH = os.getenv("TASK2_QUEUE_PATH", "queue.json")
STATE_PATH = os.getenv("TASK2_STATE_PATH", "state.json")

def fail(msg):
    print(f"TASK 2 HOLD: {msg}", file=sys.stderr)
    raise SystemExit(1)

def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        fail(f"missing required environment value: {name}")
    return value

API_VERSION = os.getenv("IG_API_VERSION", "v24.0").strip() or "v24.0"
GRAPH_HOST = (os.getenv("IG_GRAPH_HOST", "https://graph.facebook.com").strip() or "https://graph.facebook.com").rstrip("/")
IG_USER_ID = required_env("IG_USER_ID")
ACCESS_TOKEN = required_env("IG_ACCESS_TOKEN")
IMAGE_BASE_URL = required_env("IG_IMAGE_BASE_URL").rstrip("/")

def api_post(path, data):
    url = f"{GRAPH_HOST}/{API_VERSION}/{path.lstrip('/')}"
    r = requests.post(url, data=data, timeout=60)
    try: payload = r.json()
    except Exception: payload = {"raw": r.text}
    if not r.ok: fail(f"Instagram API error {r.status_code}: {payload}")
    return payload

def api_get(path, params):
    url = f"{GRAPH_HOST}/{API_VERSION}/{path.lstrip('/')}"
    r = requests.get(url, params=params, timeout=60)
    try: payload = r.json()
    except Exception: payload = {"raw": r.text}
    if not r.ok: fail(f"Instagram API error {r.status_code}: {payload}")
    return payload

def load_json(path, default):
    p = Path(path)
    if not p.exists(): return default
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc: fail(f"invalid JSON in {path}: {exc}")

def verify_public_png(url):
    try:
        r = requests.get(url, stream=True, timeout=60, allow_redirects=True)
    except Exception as exc:
        fail(f"PNG preflight request failed: {exc}")
    if not r.ok:
        fail(f"PNG preflight HTTP {r.status_code}: {url}")
    ctype = (r.headers.get("content-type") or "").lower()
    if "image/png" not in ctype and "application/octet-stream" not in ctype:
        fail(f"PNG preflight content-type is {ctype!r}")
    try:
        first = next(r.iter_content(chunk_size=64), b"")
    finally:
        r.close()
    if not first.startswith(b"\x89PNG\r\n\x1a\n"):
        fail("PNG preflight signature verification failed")

now = datetime.now(PHX)
slot = "09" if now.hour < 12 else "15"
slot_id = f"{now.date().isoformat()}-{slot}"

queue = load_json(QUEUE_PATH, [])
if not isinstance(queue, list) or len(queue) < 2:
    fail("queue.json must contain at least two distinct approved PNG filenames.")
if len(set(queue)) != len(queue):
    fail("queue.json contains duplicate filenames.")

state = load_json(STATE_PATH, {"last_slot": None, "next_index": 0, "posted": []})
if state.get("last_slot") == slot_id:
    print(f"TASK 2 PASS: slot {slot_id} already posted; duplicate suppressed.")
    raise SystemExit(0)

index = int(state.get("next_index", 0)) % len(queue)
filename = queue[index]
if not filename.lower().endswith(".png"):
    fail(f"queued asset is not a PNG: {filename}")

image_url = f"{IMAGE_BASE_URL}/{requests.utils.quote(filename)}"
verify_public_png(image_url)

media_data = {"image_url": image_url, "access_token": ACCESS_TOKEN}
container = api_post(f"{IG_USER_ID}/media", media_data)
creation_id = container.get("id")
if not creation_id: fail(f"no creation_id returned: {container}")

status = None
for _ in range(20):
    status = api_get(creation_id, {"fields": "status_code,status", "access_token": ACCESS_TOKEN})
    code = status.get("status_code")
    if code == "FINISHED": break
    if code in {"ERROR", "EXPIRED"}: fail(f"container failed: {status}")
    time.sleep(3)
else:
    fail(f"container not ready after wait: {status}")

published = api_post(f"{IG_USER_ID}/media_publish", {"creation_id": creation_id, "access_token": ACCESS_TOKEN})
media_id = published.get("id")
if not media_id: fail(f"no media_id returned: {published}")

receipt = api_get(media_id, {"fields": "id,permalink,timestamp,media_type", "access_token": ACCESS_TOKEN})
if receipt.get("id") != media_id: fail(f"receipt media id mismatch: {receipt}")
if receipt.get("media_type") != "IMAGE": fail(f"receipt media_type is not IMAGE: {receipt}")
if not receipt.get("permalink") or not receipt.get("timestamp"):
    fail(f"receipt missing permalink or timestamp: {receipt}")

state["last_slot"] = slot_id
state["next_index"] = (index + 1) % len(queue)
state.setdefault("posted", []).append({
    "slot": slot_id, "filename": filename, "media_id": media_id,
    "permalink": receipt.get("permalink"), "timestamp": receipt.get("timestamp"),
})
Path(STATE_PATH).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
print("TASK 2 PASS")
print(json.dumps(state["posted"][-1], indent=2))
