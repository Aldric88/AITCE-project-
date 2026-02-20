from bson import ObjectId
import time
from app.database import notifications_collection


def notify(user_id, type, message, link=None):
    notifications_collection.insert_one({
        "user_id": ObjectId(user_id),
        "type": type,
        "message": message,
        "link": link,
        "is_read": False,
        "created_at": int(time.time())
    })
