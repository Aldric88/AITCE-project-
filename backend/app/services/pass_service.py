import time
from bson import ObjectId

from app.database import pass_subscriptions_collection


def has_active_creator_pass(buyer_id: str, seller_id: str | ObjectId) -> bool:
    seller_oid = seller_id if isinstance(seller_id, ObjectId) else ObjectId(seller_id)
    now_ts = int(time.time())
    return (
        pass_subscriptions_collection.find_one(
            {
                "buyer_id": ObjectId(buyer_id),
                "seller_id": seller_oid,
                "status": "active",
                "expires_at": {"$gte": now_ts},
            }
        )
        is not None
    )
