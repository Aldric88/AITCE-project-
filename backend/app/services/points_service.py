import time

from bson import ObjectId

from app.database import users_collection, leaderboard_collection

MAX_WALLET_POINTS = 1_000_000


def _oid(user_id: str | ObjectId) -> ObjectId:
    if isinstance(user_id, ObjectId):
        return user_id
    return ObjectId(user_id)


def get_wallet_balance(user_id: str | ObjectId) -> int:
    user = users_collection.find_one({"_id": _oid(user_id)}, {"wallet_points": 1})
    return int((user or {}).get("wallet_points", 0))


def award_points(
    *,
    user_id: str | ObjectId,
    points: int,
    reason: str,
    txn_type: str = "credit",
    meta: dict | None = None,
) -> int:
    if int(points) <= 0:
        raise ValueError("points must be positive")
    user_oid = _oid(user_id)
    now_ts = int(time.time())
    users_collection.update_one({"_id": user_oid}, {"$inc": {"wallet_points": int(points)}})
    # Clamp to MAX_WALLET_POINTS — only fires if the increment pushed the balance over the cap
    users_collection.update_one(
        {"_id": user_oid, "wallet_points": {"$gt": MAX_WALLET_POINTS}},
        {"$set": {"wallet_points": MAX_WALLET_POINTS}},
    )
    leaderboard_collection.insert_one(
        {
            "user_id": user_oid,
            "points": int(points),
            "reason": reason,
            "txn_type": txn_type,
            "meta": meta or {},
            "created_at": now_ts,
        }
    )
    return get_wallet_balance(user_oid)


def spend_points(
    *,
    user_id: str | ObjectId,
    points: int,
    reason: str,
    txn_type: str = "debit",
    meta: dict | None = None,
) -> bool:
    if int(points) <= 0:
        raise ValueError("points must be positive")
    user_oid = _oid(user_id)
    now_ts = int(time.time())
    spent = users_collection.update_one(
        {"_id": user_oid, "wallet_points": {"$gte": int(points)}},
        {"$inc": {"wallet_points": -int(points)}},
    )
    if getattr(spent, "modified_count", 0) <= 0:
        return False
    leaderboard_collection.insert_one(
        {
            "user_id": user_oid,
            "points": -int(points),
            "reason": reason,
            "txn_type": txn_type,
            "meta": meta or {},
            "created_at": now_ts,
        }
    )
    return True
