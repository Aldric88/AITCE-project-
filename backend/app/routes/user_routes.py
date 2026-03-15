from fastapi import APIRouter, HTTPException
from app.database import users_collection, notes_collection, follows_collection
from bson import ObjectId

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{user_id}/profile")
def creator_profile(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    followers = follows_collection.count_documents({"following_id": ObjectId(user_id)})
    following = follows_collection.count_documents({"follower_id": ObjectId(user_id)})

    notes = notes_collection.find({"uploader_id": ObjectId(user_id), "status": "approved"}).sort("_id", -1).limit(30)

    notes_out = []
    for n in notes:
        notes_out.append({
            "id": str(n["_id"]),
            "title": n.get("title"),
            "subject": n.get("subject"),
            "dept": n.get("dept"),
            "semester": n.get("semester"),
            "unit": n.get("unit"),
            "is_paid": n.get("is_paid", False),
            "price": n.get("price", 0),
            "ai": n.get("ai"),
            "uploader_id": str(n.get("uploader_id"))
        })

    return {
        "creator": {
            "id": str(user["_id"]),
            "name": user.get("name"),
            "dept": user.get("dept"),
            "year": user.get("year"),
            "section": user.get("section"),
            "profile_pic_url": user.get("profile_pic_url", None),
            "verified_seller": user.get("verified_seller", False),
        },
        "followers_count": followers,
        "following_count": following,
        "notes": notes_out
    }
