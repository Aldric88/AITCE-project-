from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from bson import ObjectId

from app.database import leaderboard_collection
from app.utils.cache import cache_get_json, cache_set_json
from app.utils.dependencies import require_role
from app.services.points_service import award_points
from app.config import settings

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("/")
def leaderboard():
    cache_key = "leaderboard:top20"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    pipeline = [
        {"$group": {"_id": "$user_id", "total_points": {"$sum": "$points"}}},
        {"$sort": {"total_points": -1}},
        {"$limit": 20},
        {
            "$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "_id",
                "as": "user",
            }
        },
        {"$unwind": "$user"},
        {
            "$project": {
                "_id": 1,
                "total_points": 1,
                "name": "$user.name",
                "dept": "$user.dept",
            }
        },
    ]

    result = []
    for item in leaderboard_collection.aggregate(pipeline):
        result.append(
            {
                "user_id": str(item["_id"]),
                "name": item.get("name"),
                "dept": item.get("dept"),
                "total_points": item["total_points"],
            }
        )

    cache_set_json(cache_key, result, ttl=60)
    return result


@router.post("/rewards/top-contributors")
def reward_top_contributors(
    top_n: int = Query(default=10, ge=1, le=100),
    current_user=Depends(require_role(["admin"])),
):
    bonus = int(settings.TOP_CONTRIBUTOR_BONUS_POINTS)
    if bonus <= 0:
        return {"awarded": 0, "detail": "TOP_CONTRIBUTOR_BONUS_POINTS is disabled"}

    pipeline = [
        {"$group": {"_id": "$user_id", "total_points": {"$sum": "$points"}}},
        {"$sort": {"total_points": -1}},
        {"$limit": top_n},
    ]
    leaders = list(leaderboard_collection.aggregate(pipeline))
    if not leaders:
        return {"awarded": 0, "detail": "No contributors found"}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    reason = f"top_contributor_bonus:{today}"
    awarded = []
    for row in leaders:
        user_id = row.get("_id")
        if not isinstance(user_id, ObjectId):
            continue
        already = leaderboard_collection.find_one({"user_id": user_id, "reason": reason})
        if already:
            continue
        award_points(
            user_id=user_id,
            points=bonus,
            reason=reason,
            meta={"rank_snapshot_points": int(row.get("total_points", 0))},
        )
        awarded.append(str(user_id))

    return {
        "awarded": len(awarded),
        "bonus_points_each": bonus,
        "reason": reason,
        "user_ids": awarded,
    }
