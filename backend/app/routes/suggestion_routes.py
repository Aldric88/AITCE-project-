from bson import ObjectId
from fastapi import APIRouter, Depends
from app.database import users_collection, notes_collection, follows_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


def safe_int(x, default=0):
    try:
        return int(x)
    except:
        return default


@router.get("/creators")
def suggest_creators(current_user=Depends(get_current_user), limit: int = 10):
    """
    ✅ Suggestions based on:
    1) Highest approved note contributions
    2) Highest followers count

    ✅ Filters:
    - only same dept
    - only same year (as "semester/year group")
    - exclude current user
    - exclude already followed
    - exclude creators with too many rejected notes
    """

    me_id = ObjectId(current_user["id"])
    my_dept = current_user.get("dept")
    my_year = safe_int(current_user.get("year"))

    # ✅ already following ids
    following_cursor = follows_collection.find({"follower_id": me_id}, {"following_id": 1})
    following_ids = {f["following_id"] for f in following_cursor}

    # ✅ filter to same dept + year
    query = {
        "_id": {"$ne": me_id},
        "dept": my_dept,
        "year": my_year,
    }

    users = list(
        users_collection.find(
            query,
            {"name": 1, "dept": 1, "year": 1, "section": 1, "profile_pic_url": 1, "verified_seller": 1},
        )
    )
    if not users:
        return []

    user_ids = [u["_id"] for u in users]
    note_counts = {}
    for row in notes_collection.aggregate(
        [
            {"$match": {"uploader_id": {"$in": user_ids}, "status": {"$in": ["approved", "rejected"]}}},
            {"$group": {"_id": {"uploader_id": "$uploader_id", "status": "$status"}, "count": {"$sum": 1}}},
        ]
    ):
        uploader_id = row["_id"]["uploader_id"]
        status = row["_id"]["status"]
        if uploader_id not in note_counts:
            note_counts[uploader_id] = {"approved": 0, "rejected": 0}
        note_counts[uploader_id][status] = int(row.get("count", 0))

    follower_counts = {}
    for row in follows_collection.aggregate(
        [
            {"$match": {"following_id": {"$in": user_ids}}},
            {"$group": {"_id": "$following_id", "count": {"$sum": 1}}},
        ]
    ):
        follower_counts[row["_id"]] = int(row.get("count", 0))

    creators = []
    for u in users:
        uid = u["_id"]

        # ❌ skip if already following
        if uid in following_ids:
            continue

        # ✅ contributions (approved notes)
        approved_count = note_counts.get(uid, {}).get("approved", 0)

        # ✅ rejected (spam/low quality)
        rejected_count = note_counts.get(uid, {}).get("rejected", 0)

        # ✅ followers
        followers_count = follower_counts.get(uid, 0)

        # ✅ Exclude creators who look spammy:
        # (you can tweak this threshold)
        if rejected_count >= 3 and approved_count == 0:
            continue

        # optional: must have at least 1 approved
        if approved_count == 0:
            continue

        creators.append({
            "id": str(uid),
            "name": u.get("name"),
            "dept": u.get("dept"),
            "year": u.get("year"),
            "section": u.get("section"),
            "profile_pic_url": u.get("profile_pic_url"),
            "verified_seller": u.get("verified_seller", False),
            "contribution_count": approved_count,
            "followers_count": followers_count,
            "rejected_count": rejected_count
        })

    # ✅ Sort:
    # 1) approved contributions DESC
    # 2) followers DESC
    # 3) rejected ASC (prefer cleaner creators)
    creators.sort(
        key=lambda x: (x["contribution_count"], x["followers_count"], -x["rejected_count"]),
        reverse=True
    )

    return creators[:limit]


@router.get("/top-creators")
def top_creators_in_my_dept(current_user=Depends(get_current_user), limit: int = 20):
    """
    ✅ Leaderboard: Top creators in same dept (any year)
    ranked by:
    1) approved notes count
    2) followers count
    """

    me_id = ObjectId(current_user["id"])
    my_dept = current_user.get("dept")

    users = list(
        users_collection.find(
            {"_id": {"$ne": me_id}, "dept": my_dept},
            {"name": 1, "dept": 1, "year": 1, "section": 1, "profile_pic_url": 1, "verified_seller": 1},
        )
    )
    if not users:
        return []

    user_ids = [u["_id"] for u in users]

    approved_counts = {}
    for row in notes_collection.aggregate(
        [
            {"$match": {"uploader_id": {"$in": user_ids}, "status": "approved"}},
            {"$group": {"_id": "$uploader_id", "count": {"$sum": 1}}},
        ]
    ):
        approved_counts[row["_id"]] = int(row.get("count", 0))

    follower_counts = {}
    for row in follows_collection.aggregate(
        [
            {"$match": {"following_id": {"$in": user_ids}}},
            {"$group": {"_id": "$following_id", "count": {"$sum": 1}}},
        ]
    ):
        follower_counts[row["_id"]] = int(row.get("count", 0))

    leaderboard = []
    for u in users:
        uid = u["_id"]
        approved_count = approved_counts.get(uid, 0)
        if approved_count == 0:
            continue
        leaderboard.append(
            {
                "id": str(uid),
                "name": u.get("name"),
                "dept": u.get("dept"),
                "year": u.get("year"),
                "section": u.get("section"),
                "profile_pic_url": u.get("profile_pic_url"),
                "verified_seller": u.get("verified_seller", False),
                "contribution_count": approved_count,
                "followers_count": follower_counts.get(uid, 0),
            }
        )

    leaderboard.sort(key=lambda x: (x["contribution_count"], x["followers_count"]), reverse=True)
    return leaderboard[:limit]
