import hashlib
import json
import time
from typing import Optional

from bson import ObjectId

from app.database import idempotency_keys_collection


def make_request_fingerprint(payload: dict) -> str:
    raw = json.dumps(payload or {}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_saved_idempotent_response(route: str, user_id: str, key: str, payload_fingerprint: str) -> Optional[dict]:
    doc = idempotency_keys_collection.find_one(
        {
            "route": route,
            "user_id": ObjectId(user_id),
            "key": key,
            "payload_fingerprint": payload_fingerprint,
        }
    )
    if not doc:
        return None
    return doc.get("response")


def save_idempotent_response(route: str, user_id: str, key: str, payload_fingerprint: str, response: dict):
    idempotency_keys_collection.update_one(
        {
            "route": route,
            "user_id": ObjectId(user_id),
            "key": key,
        },
        {
            "$set": {
                "payload_fingerprint": payload_fingerprint,
                "response": response,
                "updated_at": int(time.time()),
            },
            "$setOnInsert": {
                "created_at": int(time.time()),
            },
        },
        upsert=True,
    )
