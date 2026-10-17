#!/usr/bin/env python3
import hashlib, json, os, sys, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

CONTRACT_PATH = Path("task2_contract.json")
if not CONTRACT_PATH.is_file():
    raise SystemExit("TASK 2 HOLD: task2_contract.json is missing")
try:
    CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"TASK 2 HOLD: invalid task2_contract.json: {exc}")

if CONTRACT.get("route") != "instagram_login":
    raise SystemExit("TASK 2 HOLD: Task 2 route contract mismatch")
if CONTRACT.get("timezone") != "America/Phoenix":
    raise SystemExit("TASK 2 HOLD: Task 2 timezone contract mismatch")

PHX = ZoneInfo(CONTRACT["timezone"])
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
MEDIA_COMMIT = os.getenv("TASK2_MEDIA_COMMIT", "").strip().lower()

contract_host = str(CONTRACT.get("graph_host") or "").rstrip("/")
contract_version = str(CONTRACT.get("api_version") or "").strip()
contract_username = str(CONTRACT.get("target_username") or "").strip().lstrip("@").lower()
if GRAPH_HOST != contract_host:
    fail("Instagram graph host does not match Task 2 contract")
if API_VERSION != contract_version:
    fail("Instagram API version does not match Task 2 contract")
if EXPECTED_USERNAME != contract_username:
    fail("Instagram target username does not match Task 2 contract")

missing = []
if not ACCESS_TOKEN:
    missing.append("IG_ACCESS_TOKEN")
if not IMAGE_BASE_URL:
    missing.append("IG_IMAGE_BASE_URL")
if not MEDIA_COMMIT:
    missing.append("TASK2_MEDIA_COMMIT")
if missing:
    fail("missing required environment values: " + ", ".join(missing))
if len(MEDIA_COMMIT) != 40 or any(ch not in "0123456789abcdef" for ch in MEDIA_COMMIT):
    fail("TASK2_MEDIA_COMMIT must be a full 40-character Git commit SHA")
if f"/{MEDIA_COMMIT}/instagram_media" not in IMAGE_BASE_URL:
    fail("IG_IMAGE_BASE_URL is not pinned to TASK2_MEDIA_COMMIT")

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
    if account_type not in {"BUSINESS", "MEDIA_CREATOR"}:
        fail(f"Instagram account type missing or not publish-capable: {account_type or 'MISSING'}")
    print(f"TASK 2 TARGET VERIFIED: @{username}")

def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {path}: {exc}")

def verify_public_jpeg(url, expected_sha256):
    try:
        r = requests.get(url, stream=True, timeout=60, allow_redirects=True)
    except Exception as exc:
        fail(f"JPEG preflight request failed: {exc}")
    if not r.ok:
        fail(f"JPEG preflight HTTP {r.status_code}: {url}")
    ctype = (r.headers.get("content-type") or "").lower()
    if "image/jpeg" not in ctype and "application/octet-stream" not in ctype:
        fail(f"JPEG preflight content-type is {ctype!r}")
    digest = hashlib.sha256()
    first = b""
    try:
        for chunk in r.iter_content(chunk_size=65536):
            if not chunk:
                continue
            if not first:
                first = chunk[:64]
            digest.update(chunk)
    finally:
        r.close()
    if not first.startswith(b"\xff\xd8\xff"):
        fail("JPEG preflight signature verification failed")
    actual_sha256 = digest.hexdigest()
    if actual_sha256.lower() != expected_sha256.lower():
        fail("public JPEG SHA-256 does not match validated transport artifact")
    return actual_sha256

def resolve_slot():
    explicit = os.getenv("TASK2_SLOT", "").strip()
    slots = CONTRACT.get("slots")
    if not isinstance(slots, dict) or set(slots) != {"09", "15"}:
        fail("Task 2 slot contract is invalid")
    if explicit in slots:
        return explicit
    fail("TASK2_SLOT must exactly match a contracted Task 2 lane")

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
contract_queue = CONTRACT.get("queue")
if not isinstance(contract_queue, list) or not contract_queue:
    fail("Task 2 contract queue is invalid")
if queue != contract_queue:
    fail("queue.json order/content does not exactly match Task 2 contract")
if len(set(queue)) != len(queue):
    fail("queue.json contains duplicate source filenames.")

approved = load_json("approved_source_assets.json", {})
manifest = load_json("task2_asset_manifest.json", {})
if not isinstance(approved, dict) or set(approved) != set(queue):
    fail("approved source asset control does not exactly match queue")
if not isinstance(manifest, dict) or set(manifest) != set(queue):
    fail("validated asset manifest does not exactly match queue")
for source_name in queue:
    approved_entry = approved.get(source_name)
    manifest_entry = manifest.get(source_name)
    if not isinstance(approved_entry, dict) or not isinstance(manifest_entry, dict):
        fail(f"asset control entry invalid: {source_name}")
    approved_source_sha = str(approved_entry.get("source_sha256") or "").lower()
    manifest_source_sha = str(manifest_entry.get("source_sha256") or "").lower()
    publish_asset = str(manifest_entry.get("publish_asset") or "")
    publish_sha = str(manifest_entry.get("publish_sha256") or "").lower()
    if len(approved_source_sha) != 64 or manifest_source_sha != approved_source_sha:
        fail(f"approved source SHA-256 control mismatch: {source_name}")
    if publish_asset != Path(source_name).with_suffix(".jpg").name:
        fail(f"validated transport filename mismatch: {source_name}")
    if len(publish_sha) != 64:
        fail(f"validated transport SHA-256 missing/invalid: {source_name}")

state = load_json(STATE_PATH, {"last_slot": None, "next_index": 0, "posted": []})
if not isinstance(state, dict):
    fail("state.json root must be an object")
posted_history = state.get("posted", [])
if not isinstance(posted_history, list):
    fail("state posted field must be a list")
try:
    next_index_raw = int(state.get("next_index", 0))
except Exception:
    fail("state next_index must be an integer")
if next_index_raw < 0 or next_index_raw >= len(queue):
    fail(f"state next_index out of range: {next_index_raw}")
seen_slots = set()
seen_media_ids = set()
seen_permalinks = set()
for i, item in enumerate(posted_history):
    if not isinstance(item, dict):
        fail(f"state posted[{i}] must be an object")
    required_history = ("slot", "filename", "publish_asset", "publish_sha256", "publish_commit", "media_id", "permalink", "timestamp", "username")
    missing_history = [k for k in required_history if not str(item.get(k, "")).strip()]
    if missing_history:
        fail(f"state posted[{i}] incomplete: " + ", ".join(missing_history))
    if item["filename"] not in queue:
        fail(f"state posted[{i}] source asset is not approved: {item['filename']}")
    history_entry = manifest.get(item["filename"])
    history_approved = approved.get(item["filename"])
    if not isinstance(history_entry, dict) or not isinstance(history_approved, dict):
        fail(f"state posted[{i}] asset controls missing")
    if history_entry.get("source_sha256") != history_approved.get("source_sha256"):
        fail(f"state posted[{i}] approved source SHA-256 mismatch")
    if item["publish_asset"] != history_entry.get("publish_asset"):
        fail(f"state posted[{i}] transport asset mismatch")
    if item["publish_sha256"] != history_entry.get("publish_sha256"):
        fail(f"state posted[{i}] transport SHA-256 mismatch")
    publish_commit = str(item.get("publish_commit") or "").lower()
    if len(publish_commit) != 40 or any(ch not in "0123456789abcdef" for ch in publish_commit):
        fail(f"state posted[{i}] publish commit invalid")
    if str(item["username"]).strip().lower() != EXPECTED_USERNAME:
        fail(f"state posted[{i}] username mismatch")
    if item["slot"] in seen_slots:
        fail(f"duplicate slot in state history: {item['slot']}")
    if str(item["media_id"]) in seen_media_ids:
        fail(f"duplicate media_id in state history: {item['media_id']}")
    if str(item["permalink"]) in seen_permalinks:
        fail(f"duplicate permalink in state history: {item['permalink']}")
    seen_slots.add(item["slot"])
    seen_media_ids.add(str(item["media_id"]))
    seen_permalinks.add(str(item["permalink"]))
if state.get("last_slot") is not None and state.get("last_slot") not in seen_slots:
    fail("state last_slot does not reference a verified posted receipt")
if state.get("last_slot") == slot_id:
    matches = [x for x in state.get("posted", []) if x.get("slot") == slot_id]
    if len(matches) != 1:
        fail(f"state claims slot {slot_id} posted but does not contain exactly one receipt")
    receipt = matches[0]
    required = ("filename", "publish_asset", "publish_sha256", "publish_commit", "media_id", "permalink", "timestamp", "username")
    missing = [k for k in required if not str(receipt.get(k, "")).strip()]
    if missing:
        fail("stored receipt is incomplete: " + ", ".join(missing))
    if receipt["filename"] not in queue:
        fail("stored receipt source asset is not approved")
    duplicate_entry = manifest.get(receipt["filename"])
    duplicate_approved = approved.get(receipt["filename"])
    if not isinstance(duplicate_entry, dict) or not isinstance(duplicate_approved, dict):
        fail("stored receipt asset controls missing")
    if duplicate_entry.get("source_sha256") != duplicate_approved.get("source_sha256"):
        fail("stored receipt approved source SHA-256 mismatch")
    if receipt["publish_asset"] != duplicate_entry.get("publish_asset"):
        fail("stored receipt transport asset mismatch")
    if receipt["publish_sha256"] != duplicate_entry.get("publish_sha256"):
        fail("stored receipt transport SHA-256 mismatch")
    stored_commit = str(receipt["publish_commit"]).strip().lower()
    if len(stored_commit) != 40 or any(ch not in "0123456789abcdef" for ch in stored_commit):
        fail("stored receipt immutable media commit invalid")
    stored_image_url = (
        "https://raw.githubusercontent.com/"
        f"JeffBrown777/GDXP-Task2-Instagram/{stored_commit}/instagram_media/"
        f"{requests.utils.quote(receipt['publish_asset'])}"
    )
    verify_public_jpeg(stored_image_url, str(receipt["publish_sha256"]))
    expected_next = (queue.index(receipt["filename"]) + 1) % len(queue)
    if next_index_raw != expected_next:
        fail("stored receipt queue advancement mismatch")
    if str(receipt.get("username", "")).strip().lower() != EXPECTED_USERNAME:
        fail(f"stored receipt username mismatch: {receipt.get('username')}")
    live = api_get(str(receipt["media_id"]), {
        "fields": "id,permalink,timestamp,media_type,username",
        "access_token": ACCESS_TOKEN,
    })
    if str(live.get("id") or "") != str(receipt["media_id"]):
        fail(f"stored receipt media_id no longer verifies: {live}")
    if str(live.get("username") or "").strip().lower() != EXPECTED_USERNAME:
        fail(f"stored receipt live username mismatch: {live}")
    if live.get("media_type") != "IMAGE":
        fail(f"stored receipt live media_type mismatch: {live}")
    if str(live.get("permalink") or "") != str(receipt["permalink"]):
        fail(f"stored receipt permalink mismatch: {live}")
    if str(live.get("timestamp") or "") != str(receipt["timestamp"]):
        fail(f"stored receipt timestamp mismatch: {live}")
    try:
        live_time = datetime.fromisoformat(str(live["timestamp"]).replace("Z", "+00:00"))
    except Exception:
        fail(f"stored receipt live timestamp is not valid ISO-8601: {live}")
    if live_time.astimezone(PHX).date() != now.date():
        fail(f"stored receipt live PHX date mismatch: {live}")
    print(f"TASK 2 PASS: slot {slot_id} has a live reverified Instagram receipt; duplicate suppressed.")
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0)

index = next_index_raw
filename = queue[index]
if not filename.lower().endswith(".png"):
    fail(f"queued source asset is not a PNG: {filename}")

publish_filename = Path(filename).with_suffix(".jpg").name
entry = manifest.get(filename) if isinstance(manifest, dict) else None
if not isinstance(entry, dict):
    fail(f"validated asset manifest missing source entry: {filename}")
if entry.get("publish_asset") != publish_filename:
    fail(f"validated asset manifest transport mismatch: {filename}")
expected_publish_sha256 = str(entry.get("publish_sha256") or "").strip()
if len(expected_publish_sha256) != 64:
    fail(f"validated asset manifest SHA-256 missing/invalid: {filename}")
image_url = f"{IMAGE_BASE_URL}/{requests.utils.quote(publish_filename)}"
publish_sha256 = verify_public_jpeg(image_url, expected_publish_sha256)

container = api_post(f"{IG_USER_ID}/media", {
    "image_url": image_url,
    "access_token": ACCESS_TOKEN,
})
creation_id = container.get("id")
if not creation_id:
    fail(f"no creation_id returned: {container}")

status = None
for attempt in range(5):
    status = api_get(creation_id, {
        "fields": "status_code,status",
        "access_token": ACCESS_TOKEN,
    })
    code = status.get("status_code")
    if code == "FINISHED":
        break
    if code in {"ERROR", "EXPIRED", "PUBLISHED"}:
        fail(f"container entered non-publishable terminal state: {status}")
    if code != "IN_PROGRESS":
        fail(f"container returned unknown status_code: {status}")
    if attempt < 4:
        time.sleep(60)
else:
    fail(f"container not ready after five one-minute status checks: {status}")

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
if not str(receipt.get("username") or "").strip():
    fail(f"receipt missing username: {receipt}")
if str(receipt.get("username")).strip().lower() != EXPECTED_USERNAME:
    fail(f"receipt username mismatch: {receipt}")
if not receipt.get("permalink") or not receipt.get("timestamp"):
    fail(f"receipt missing permalink or timestamp: {receipt}")
try:
    receipt_time = datetime.fromisoformat(str(receipt["timestamp"]).replace("Z", "+00:00"))
except Exception:
    fail(f"receipt timestamp is not valid ISO-8601: {receipt}")
if receipt_time.astimezone(PHX).date() != now.date():
    fail(f"receipt PHX date mismatch: {receipt}")

posted = state.setdefault("posted", [])
if not isinstance(posted, list):
    fail("state posted field is not a list")
if any(str(x.get("media_id") or "") == str(media_id) for x in posted if isinstance(x, dict)):
    fail(f"media_id already exists in state history: {media_id}")
if any(str(x.get("permalink") or "") == str(receipt.get("permalink") or "") for x in posted if isinstance(x, dict)):
    fail("permalink already exists in state history")

record = {
    "slot": slot_id,
    "filename": filename,
    "publish_asset": publish_filename,
    "publish_sha256": publish_sha256,
    "publish_commit": MEDIA_COMMIT,
    "media_id": media_id,
    "permalink": receipt.get("permalink"),
    "timestamp": receipt.get("timestamp"),
    "username": receipt.get("username"),
}
state["last_slot"] = slot_id
state["next_index"] = (index + 1) % len(queue)
posted.append(record)

state_path = Path(STATE_PATH)
tmp_path = state_path.with_name(state_path.name + ".tmp")
with tmp_path.open("w", encoding="utf-8") as f:
    f.write(json.dumps(state, indent=2) + "\n")
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp_path, state_path)

verified_state = load_json(STATE_PATH, {})
if verified_state.get("last_slot") != slot_id:
    fail("atomic state verification failed after write")
matches = [x for x in verified_state.get("posted", []) if isinstance(x, dict) and x.get("slot") == slot_id]
if len(matches) != 1 or matches[0] != record:
    fail("atomic state receipt verification failed after write")

print("TASK 2 PASS")
print(json.dumps(record, indent=2))
