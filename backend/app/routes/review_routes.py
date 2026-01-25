import time
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import reviews_collection, notes_collection, purchases_collection
from app.schemas.review_schema import ReviewCreate
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/note/{note_id}")
def add_review(note_id: str, data: ReviewCreate, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Cannot review unapproved note")

    # ✅ allow only 1 review per user per note
    existing = reviews_collection.find_one({
        "note_id": ObjectId(note_id),
        "user_id": ObjectId(current_user["id"])
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this note")

    verified_purchase = False
    if note.get("is_paid", False):
        purchase = purchases_collection.find_one({
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(current_user["id"]),
            "status": "success"
        })
        verified_purchase = True if purchase else False

        # ✅ Paid note review allowed only if purchased
        if not verified_purchase and str(note["uploader_id"]) != current_user["id"]:
            raise HTTPException(status_code=403, detail="Buy note to review")

    review_doc = {
        "note_id": ObjectId(note_id),
        "user_id": ObjectId(current_user["id"]),
        "rating": data.rating,
        "comment": data.comment,
        "verified_purchase": verified_purchase,
        "created_at": int(time.time()),
    }

    reviews_collection.insert_one(review_doc)

    return {"message": "Review added ✅"}


@router.get("/note/{note_id}")
def get_reviews(note_id: str):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    reviews = reviews_collection.find({"note_id": ObjectId(note_id)}).sort("_id", -1)

    result = []
    for r in reviews:
        result.append({
            "id": str(r["_id"]),
            "note_id": str(r["note_id"]),
            "user_id": str(r["user_id"]),
            "rating": r["rating"],
            "comment": r.get("comment"),
            "verified_purchase": r.get("verified_purchase", False),
            "created_at": r.get("created_at"),
        })

    return result


@router.get("/note/{note_id}/summary")
def review_summary(note_id: str):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    pipeline = [
        {"$match": {"note_id": ObjectId(note_id)}},
        {"$group": {"_id": "$note_id", "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    data = list(reviews_collection.aggregate(pipeline))
    if not data:
        return {"avg_rating": 0, "count": 0}

    return {"avg_rating": round(data[0]["avg_rating"], 2), "count": data[0]["count"]}
