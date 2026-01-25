import time
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import notes_collection, purchases_collection, users_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/purchases", tags=["Purchases"])


@router.get("/my")
def my_purchases(current_user=Depends(get_current_user)):
    purchases = purchases_collection.find(
        {"buyer_id": ObjectId(current_user["id"]), "status": "success"}
    ).sort("_id", -1)

    result = []
    for p in purchases:
        note = notes_collection.find_one({"_id": p["note_id"]})
        if note:
            result.append({
                "purchase_id": str(p["_id"]),
                "note_id": str(p["note_id"]),
                "amount": p.get("amount", 0),
                "created_at": p.get("created_at"),
                "note": {
                    "id": str(note["_id"]),
                    "title": note.get("title"),
                    "dept": note.get("dept"),
                    "subject": note.get("subject"),
                    "semester": note.get("semester"),
                    "unit": note.get("unit"),
                    "is_paid": note.get("is_paid", False),
                    "price": note.get("price", 0),
                    "note_type": note.get("note_type"),
                    "status": note.get("status"),
                }
            })

    return result


@router.post("/{note_id}/buy")
def buy_note(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Note not available")

    if not note.get("is_paid", False):
        return {"message": "This note is free ✅"}

    already = purchases_collection.find_one(
        {
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(current_user["id"]),
            "status": "success",
        }
    )

    if already:
        return {"message": "Already purchased ✅"}

    # MVP: Mock Payment Success
    purchases_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(current_user["id"]),
            "amount": note.get("price", 0),
            "status": "success",
            "payment_provider": "mock",
            "created_at": int(time.time()),
        }
    )

    return {
        "message": "Purchase successful ✅ (mock)",
        "note_id": note_id,
    }


@router.get("/{note_id}/has-access")
def has_access(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if not note.get("is_paid", False):
        return {"has_access": True}

    purchase = purchases_collection.find_one(
        {
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(current_user["id"]),
            "status": "success",
        }
    )

    return {"has_access": True if purchase else False}
