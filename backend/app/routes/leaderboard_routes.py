from fastapi import APIRouter
from bson import ObjectId

from app.database import leaderboard_collection, users_collection

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("/")
def leaderboard():
    pipeline = [
        {"$group": {"_id": "$user_id", "total_points": {"$sum": "$points"}}},
        {"$sort": {"total_points": -1}},
        {"$limit": 20},
    ]

    data = list(leaderboard_collection.aggregate(pipeline))

    result = []
    for item in data:
        user = users_collection.find_one({"_id": item["_id"]})
        if user:
            result.append(
                {
                    "user_id": str(item["_id"]),
                    "name": user.get("name"),
                    "dept": user.get("dept"),
                    "total_points": item["total_points"],
                }
            )

    return result
