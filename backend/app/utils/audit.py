import time
from bson import ObjectId

from app.database import audit_events_collection


def log_audit_event(event_type: str, actor_id: str | None, note_id: str | None, payload: dict):
    doc = {
        "event_type": event_type,
        "payload": payload or {},
        "created_at": int(time.time()),
    }
    if actor_id and ObjectId.is_valid(str(actor_id)):
        doc["actor_id"] = ObjectId(str(actor_id))
    if note_id and ObjectId.is_valid(str(note_id)):
        doc["note_id"] = ObjectId(str(note_id))
    audit_events_collection.insert_one(doc)
