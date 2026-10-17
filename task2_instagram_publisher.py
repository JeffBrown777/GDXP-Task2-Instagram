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

API_VERSION = os.getenv("IG_API_VERSION", "v24.0").strip() or "v24.0"
GRAPH_HOST = (os.getenv("IG_GRAPH_HOST", "https://graph.instagram.com").strip() or "https://graph.instagram.com").rstrip("/")
ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "").strip()
IMAGE_BASE_URL = os.getenv("IG_IMAGE_BASE_URL", "").strip().rstrip("/")
EXPECTED_USERNAME = os.getenv("IG_EXPECTED_USERNAME", "jeffbrown3579").strip().lstrip("@").lower()
IG_USER_ID = os.getenv("IG_USER_ID", "").strip()

missing = []
if not ACCESS_TOKEN:
    missing.append("IG_ACCESS_TOKEN")
if not IMAGE_BASE_URL:
    missing.append("IG_IMAGE_BASE_URL")
if missing:
    fail("missing required environment values: " + ", ".join(missing))

def api_post(path, data):
    url = f"{GRAPH_HOST}/{API_VERSION}/{path.lstrip('/')}"
    r = requests.post(url, data=data, timeout=60)
    try:
        payload = r.json()
    except Exception:
        payload = {"raw": r.text}
    if not r.ok:
        fail(f"Instagram API error {r.status_code}: {payload}")
    return payload

def api_get(path, params):
    url = f"{GRAPH_HOST}/{API_VERSION}/{path.lstrip('/')}"
    r = requests.get(url, params=params, timeout=60)
    try:
        payload = r.json()
    except Exception:
        payload = {"raw": r.text}
    if not r.ok:
        fail(f"Instagram API error {r.status_code}: {payload}")
    return payload

def normalize_profile(payload):
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        if len(payload["data"]) != 1:
            fail(f"Instagram profile lookup returned {len(payload['data'])} accounts; refusing to guess target")
        return payload["data"][0]
    return payload

def resolve_account():
    global IG_USER_ID
    profile = normalize_profile(api_get("me", {
        "fields": "user_id,username,id,account_type",
        "access_token": ACCESS_TOKEN,
    }))
    username = str(profile.get("username") or "").strip().lstrip("@").lower()
    if not username:
        fail(f"Instagram profile lookup did not return username: {profile}")
    if EXPECTED_USERNAME and username != EXPECTED_USERNAME:
        fail(f"wrong Instagram target account: @{username}; expected @{EXPECTED_USERNAME}")
    resolved = str(profile.get("user_id") or profile.get("id") or "").strip()
    if not resolved:
        fail(f"Instagram profile lookup did not return a usable account id: {profile}")
    if IG_USER_ID and IG_USER_ID != resolved:
        fail("configured IG_USER_ID does not match authenticated Instagram account")
    IG_USER_ID = resolved
    account_type = str(profile.get("account_type") or "").upper()
    if account_type and account_type not in {"BUSINESS", "MEDIA_CREATOR", "CREATOR"}:
        fail(f"Instagram account is not a publish-capable professional account: {account_type}")
    print(f"TASK 2 TARGET VERIFIED: @{username}")

def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {path}: {exc}")

def verify_public_jpeg(url):
    try:
        r = requests.get(url, stream=True, timeout=60, allow_redirects=True)
    except Exception as exc:
        fail(f"JPEG preflight request failed: {exc}")
    if not r.ok:
        fail(f"JPEG preflight HTTP {r.status_code}: {url}")
    ctype = (r.headers.get("content-type") or "").lower()
    if "image/jpeg" not in ctype and "application/octet-stream" not in ctype:
        fail(f"JPEG preflight content-type is {ctype!r}")
    try:
        first = next(r.iter_content(chunk_size=64), b"")
    finally:
        r.close()
    if not first.startswith(b"\xff\xd8\xff"):
        fail("JPEG preflight signature verification failed")

def resolve_slot():
    explicit = os.getenv("TASK2_SLOT", "").strip()
    if explicit in {"09", "15"}:
        return explicit
    now = datetime.now(PHX)
    return "09" if now.hour < 12 else "15"

resolve_account()

limit_payload = api_get(f"{IG_USER_ID}/content_publishing_limit", {
    "fields": "quota_usage,config",
    "access_token": ACCESS_TOKEN,
})
limit_rows = limit_payload.get("data") if isinstance(limit_payload, dict) else None
if not isinstance(limit_rows, list) or len(limit_rows) != 1:
    fail(f"unexpected content publishing limit response: {limit_payload}")
limit_row = limit_rows[0]
quota_usage = int(limit_row.get("quota_usage", 0))
quota_config = limit_row.get("config") or {}
quota_total = quota_config.get("quota_total")
if quota_total is not None and quota_usage >= int(quota_total):
    fail(f"Instagram publishing quota exhausted: {quota_usage}/{quota_total}")
print(f"TASK 2 PUBLISHING QUOTA VERIFIED: {quota_usage}/{quota_total if quota_total is not None else 'runtime limit unavailable'}")

now = datetime.now(PHX)
slot = resolve_slot()
slot_id = f"{now.date().isoformat()}-{slot}"

queue = load_json(QUEUE_PATH, [])
if not isinstance(queue, list) or len(queue) < 2:
    fail("queue.json must contain at least two distinct approved PNG source filenames.")
if len(set(queue)) != len(queue):
    fail("queue.json contains duplicate source filenames.")

state = load_json(STATE_PATH, {"last_slot": None, "next_index": 0, "posted": []})
if state.get("last_slot") == slot_id:
    matches = [x for x in state.get("posted", []) if x.get("slot") == slot_id]
    if not matches:
        fail(f"state claims slot {slot_id} posted but no receipt exists")
    receipt = matches[-1]
    required = ("filename", "media_id", "permalink", "timestamp", "username")
    missing = [k for k in required if not str(receipt.get(k, "")).strip()]
    if missing:
        fail("stored receipt is incomplete: " + ", ".join(missing))
    if str(receipt.get("username", "")).lower() != EXPECTED_USERNAME:
        fail(f"stored receipt username mismatch: {receipt.get('username')}")
    print(f"TASK 2 PASS: slot {slot_id} already has a verified Instagram receipt; duplicate suppressed.")
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0)

index = int(state.get("next_index", 0)) % len(queue)
filename = queue[index]
if not filename.lower().endswith(".png"):
    fail(f"queued source asset is not a PNG: {filename}")

publish_filename = Path(filename).with_suffix(".jpg").name
image_url = f"{IMAGE_BASE_URL}/{requests.utils.quote(publish_filename)}"
verify_public_jpeg(image_url)

container = api_post(f"{IG_USER_ID}/media", {
    "image_url": image_url,
    "access_token": ACCESS_TOKEN,
})
creation_id = container.get("id")
if not creation_id:
    fail(f"no creation_id returned: {container}")

status = None
for _ in range(20):
    status = api_get(creation_id, {
        "fields": "status_code,status",
        "access_token": ACCESS_TOKEN,
    })
    code = status.get("status_code")
    if code == "FINISHED":
        break
    if code in {"ERROR", "EXPIRED"}:
        fail(f"container failed: {status}")
    time.sleep(3)
else:
    fail(f"container not ready after wait: {status}")

published = api_post(f"{IG_USER_ID}/media_publish", {
    "creation_id": creation_id,
    "access_token": ACCESS_TOKEN,
})
media_id = published.get("id")
if not media_id:
    fail(f"no media_id returned: {published}")

receipt = api_get(media_id, {
    "fields": "id,permalink,timestamp,media_type,username",
    "access_token": ACCESS_TOKEN,
})
if receipt.get("id") != media_id:
    fail(f"receipt media id mismatch: {receipt}")
if receipt.get("media_type") != "IMAGE":
    fail(f"receipt media_type is not IMAGE: {receipt}")
if receipt.get("username") and str(receipt.get("username")).lower() != EXPECTED_USERNAME:
    fail(f"receipt username mismatch: {receipt}")
if not receipt.get("permalink") or not receipt.get("timestamp"):
    fail(f"receipt missing permalink or timestamp: {receipt}")
try:
    receipt_time = datetime.fromisoformat(str(receipt["timestamp"]).replace("Z", "+00:00"))
except Exception:
    fail(f"receipt timestamp is not valid ISO-8601: {receipt}")
if receipt_time.astimezone(PHX).date() != now.date():
    fail(f"receipt PHX date mismatch: {receipt}")

state["last_slot"] = slot_id
state["next_index"] = (index + 1) % len(queue)
state.setdefault("posted", []).append({
    "slot": slot_id,
    "filename": filename,
    "publish_asset": publish_filename,
    "media_id": media_id,
    "permalink": receipt.get("permalink"),
    "timestamp": receipt.get("timestamp"),
    "username": receipt.get("username") or EXPECTED_USERNAME,
})
Path(STATE_PATH).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
print("TASK 2 PASS")
print(json.dumps(state["posted"][-1], indent=2))
