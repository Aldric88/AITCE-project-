from fastapi import APIRouter
from bson import ObjectId

from app.database import leaderboard_collection
from app.utils.cache import cache_get_json, cache_set_json

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
