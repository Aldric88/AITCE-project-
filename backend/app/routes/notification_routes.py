import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from bson import ObjectId
import time

from app.database import notifications_collection, users_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])
_STREAM_SNAPSHOT_CACHE: dict[str, dict] = {}
_STREAM_SNAPSHOT_TTL_SECONDS = 5


class NotificationPreferencesUpdate(BaseModel):
    realtime_enabled: bool = True
    digest_enabled: bool = True
    enabled_types: list[str] = []


@router.get("/")
def my_notifications(current_user=Depends(get_current_user)):
    notes = notifications_collection.find(
        {"user_id": ObjectId(current_user["id"])}
    ).sort("created_at", -1).limit(50)

    out = []
    for n in notes:
        out.append({
            "id": str(n["_id"]),
            "type": n["type"],
            "message": n["message"],
            "link": n.get("link"),
            "is_read": n.get("is_read", False),
            "created_at": n["created_at"]
        })
    return out


@router.post("/{notification_id}/read")
def mark_as_read(notification_id: str, current_user=Depends(get_current_user)):
    notifications_collection.update_one(
        {
            "_id": ObjectId(notification_id),
            "user_id": ObjectId(current_user["id"])
        },
        {"$set": {"is_read": True}}
    )
    return {"message": "Marked as read"}


@router.post("/read-all")
def mark_all_as_read(current_user=Depends(get_current_user)):
    res = notifications_collection.update_many(
        {"user_id": ObjectId(current_user["id"]), "is_read": False},
        {"$set": {"is_read": True}},
    )
    return {"message": "All notifications marked as read", "updated": res.modified_count}


@router.get("/unread-count")
def unread_count(current_user=Depends(get_current_user)):
    count = notifications_collection.count_documents({"user_id": ObjectId(current_user["id"]), "is_read": False})
    return {"unread": count}


@router.get("/preferences")
def get_preferences(current_user=Depends(get_current_user)):
    user = users_collection.find_one({"_id": ObjectId(current_user["id"])}, {"notification_prefs": 1})
    prefs = (user or {}).get("notification_prefs") or {}
    return {
        "realtime_enabled": prefs.get("realtime_enabled", True),
        "digest_enabled": prefs.get("digest_enabled", True),
        "enabled_types": prefs.get("enabled_types", []),
    }


@router.patch("/preferences")
def update_preferences(data: NotificationPreferencesUpdate, current_user=Depends(get_current_user)):
    users_collection.update_one(
        {"_id": ObjectId(current_user["id"])},
        {
            "$set": {
                "notification_prefs.realtime_enabled": data.realtime_enabled,
                "notification_prefs.digest_enabled": data.digest_enabled,
                "notification_prefs.enabled_types": data.enabled_types,
            }
        },
    )
    return {"message": "Notification preferences updated ✅"}


@router.get("/digest")
def digest(current_user=Depends(get_current_user)):
    since = int(time.time()) - (24 * 60 * 60)
    rows = list(
        notifications_collection.find(
            {"user_id": ObjectId(current_user["id"]), "created_at": {"$gte": since}}
        )
    )
    by_type = {}
    for n in rows:
        t = n.get("type", "general")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "window_hours": 24,
        "total": len(rows),
        "by_type": [{"type": k, "count": v} for k, v in sorted(by_type.items(), key=lambda x: x[1], reverse=True)],
    }


@router.get("/stream")
async def notification_stream(current_user=Depends(get_current_user)):
    user_oid = ObjectId(current_user["id"])
    user_key = str(user_oid)

    def get_snapshot(now_ts: int):
        cached = _STREAM_SNAPSHOT_CACHE.get(user_key)
        if cached and int(cached.get("expires_at", 0)) > now_ts:
            return cached["payload"]

        latest = notifications_collection.find_one(
            {"user_id": user_oid},
            {"type": 1, "message": 1, "created_at": 1},
            sort=[("created_at", -1)],
        )
        unread = notifications_collection.count_documents({"user_id": user_oid, "is_read": False})
        payload = {
            "unread": unread,
            "latest": {
                "id": str(latest["_id"]),
                "type": latest.get("type"),
                "message": latest.get("message"),
                "created_at": latest.get("created_at"),
            } if latest else None,
        }
        _STREAM_SNAPSHOT_CACHE[user_key] = {
            "expires_at": now_ts + _STREAM_SNAPSHOT_TTL_SECONDS,
            "payload": payload,
        }
        return payload

    async def event_generator():
        last_payload = None
        while True:
            now_ts = int(time.time())
            payload = get_snapshot(now_ts)
            if payload != last_payload:
                last_payload = payload
                yield f"data: {json.dumps(payload, ensure_ascii=True)}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
