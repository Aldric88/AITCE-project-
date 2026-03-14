from bson import ObjectId
import time
from app.database import notifications_collection, users_collection
from app.utils.notification_bus import publish_notification


def notify(user_id, type, message, link=None):
    user = users_collection.find_one({"_id": ObjectId(user_id)}, {"notification_prefs": 1})
    prefs = (user or {}).get("notification_prefs") or {}
    if prefs.get("realtime_enabled") is False:
        return
    enabled_types = prefs.get("enabled_types") or []
    if enabled_types and type not in enabled_types:
        return
    notifications_collection.insert_one({
        "user_id": ObjectId(user_id),
        "type": type,
        "message": message,
        "link": link,
        "is_read": False,
        "created_at": int(time.time())
    })
    publish_notification(str(user_id))
