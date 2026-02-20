import time
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.database import disputes_collection, purchases_collection, notes_collection
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/disputes", tags=["Disputes"])


class DisputeCreate(BaseModel):
    message: str


@router.post("/note/{note_id}")
def raise_dispute(note_id: str, data: DisputeCreate, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    # must have purchased
    purchase = purchases_collection.find_one({
        "note_id": ObjectId(note_id),
        "$or": [
            {"buyer_id": ObjectId(current_user["id"]), "status": "success"},
            {"user_id": ObjectId(current_user["id"]), "status": {"$in": ["success", "paid", "free"]}},
        ],
    })
    if not purchase:
        raise HTTPException(status_code=403, detail="You can dispute only after purchase")

    disputes_collection.insert_one({
        "note_id": ObjectId(note_id),
        "buyer_id": ObjectId(current_user["id"]),
        "message": data.message,
        "status": "pending",  # pending / approved / rejected
        "created_at": int(time.time())
    })

    return {"message": "Dispute submitted ✅"}


@router.get("/pending")
def pending_disputes(current_user=Depends(require_role(["admin"]))):
    disputes = disputes_collection.find({"status": "pending"}).sort("_id", -1)

    result = []
    for d in disputes:
        result.append({
            "id": str(d["_id"]),
            "note_id": str(d["note_id"]),
            "buyer_id": str(d["buyer_id"]),
            "message": d["message"],
            "status": d["status"],
            "created_at": d["created_at"],
        })

    return result


@router.patch("/{dispute_id}/approve")
def approve_dispute(dispute_id: str, current_user=Depends(require_role(["admin"]))):
    if not ObjectId.is_valid(dispute_id):
        raise HTTPException(status_code=400, detail="Invalid dispute_id")

    disputes_collection.update_one(
        {"_id": ObjectId(dispute_id)},
        {"$set": {"status": "approved"}}
    )

    # MVP: mock refund record only
    return {"message": "Dispute approved ✅ (mock refund done)"}


@router.patch("/{dispute_id}/reject")
def reject_dispute(dispute_id: str, current_user=Depends(require_role(["admin"]))):
    if not ObjectId.is_valid(dispute_id):
        raise HTTPException(status_code=400, detail="Invalid dispute_id")

    disputes_collection.update_one(
        {"_id": ObjectId(dispute_id)},
        {"$set": {"status": "rejected"}}
    )

    return {"message": "Dispute rejected ✅"}
