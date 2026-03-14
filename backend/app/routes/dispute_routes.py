import time
import os
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.database import disputes_collection, purchases_collection, notes_collection
from app.utils.dependencies import get_current_user, require_role
from app.services.ledger_service import add_ledger_entry
from app.services.points_service import award_points, spend_points
from app.utils.notify import notify

try:
    import razorpay
except Exception:  # pragma: no cover
    razorpay = None

_RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
_RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
_razorpay_client = (
    razorpay.Client(auth=(_RAZORPAY_KEY_ID, _RAZORPAY_KEY_SECRET))
    if razorpay and _RAZORPAY_KEY_ID and _RAZORPAY_KEY_SECRET
    else None
)

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

    # Idempotency: block duplicate open disputes for the same note
    existing = disputes_collection.find_one({
        "note_id": ObjectId(note_id),
        "buyer_id": ObjectId(current_user["id"]),
        "status": "pending",
    })
    if existing:
        raise HTTPException(status_code=409, detail="You already have a pending dispute for this note")

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
    dispute = disputes_collection.find_one({"_id": ObjectId(dispute_id)})
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute.get("status") != "pending":
        return {"message": "Dispute already processed", "status": dispute.get("status")}

    note = notes_collection.find_one({"_id": dispute["note_id"]})
    purchase = purchases_collection.find_one(
        {
            "note_id": dispute["note_id"],
            "$or": [
                {"buyer_id": dispute["buyer_id"], "status": "success"},
                {"user_id": dispute["buyer_id"], "status": {"$in": ["success", "paid"]}},
            ],
        },
        sort=[("created_at", -1)],
    )
    if not purchase:
        raise HTTPException(status_code=404, detail="Matching successful purchase not found")

    disputes_collection.update_one(
        {"_id": ObjectId(dispute_id)},
        {
            "$set": {
                "status": "approved",
                "refund_status": "refund_initiated",
                "approved_at": int(time.time()),
                "approved_by": current_user["id"],
            }
        },
    )

    refund_status = "refund_failed"
    refund_id = None
    amount = int(purchase.get("amount", 0))
    currency = str(purchase.get("currency", "INR")).upper()

    if currency == "POINTS" or purchase.get("purchase_type") == "points":
        buyer_id = purchase.get("buyer_id") or purchase.get("user_id")
        seller_id = note.get("uploader_id") if note else purchase.get("seller_id")
        award_points(
            user_id=buyer_id,
            points=max(amount, 0),
            reason="dispute_refund_points_credit",
            meta={"dispute_id": dispute_id, "purchase_id": str(purchase["_id"])},
        )
        if seller_id and amount > 0:
            spend_points(
                user_id=seller_id,
                points=amount,
                reason="dispute_refund_points_debit",
                meta={"dispute_id": dispute_id, "purchase_id": str(purchase["_id"])},
            )
        refund_status = "refund_success"
    else:
        payment_id = purchase.get("razorpay_payment_id")
        if _razorpay_client and payment_id and amount > 0:
            try:
                refund = _razorpay_client.payment.refund(payment_id, {"amount": amount * 100})
                refund_id = refund.get("id")
                refund_status = "refund_success"
            except Exception:
                refund_status = "refund_failed"

    purchases_collection.update_one(
        {"_id": purchase["_id"]},
        {
            "$set": {
                "status": "refunded" if refund_status == "refund_success" else purchase.get("status"),
                "refund_status": refund_status,
                "refunded_at": int(time.time()) if refund_status == "refund_success" else None,
                "refund_id": refund_id,
            }
        },
    )
    disputes_collection.update_one(
        {"_id": ObjectId(dispute_id)},
        {"$set": {"refund_status": refund_status, "refund_id": refund_id}},
    )
    if refund_status == "refund_success" and note:
        add_ledger_entry(
            purchase_id=purchase["_id"],
            buyer_id=purchase.get("buyer_id") or purchase.get("user_id"),
            seller_id=note["uploader_id"],
            note_id=purchase["note_id"],
            amount=-abs(amount),
            currency=currency or "INR",
            entry_type="refund",
            source="disputes.approve",
            metadata={"dispute_id": dispute_id, "refund_id": refund_id},
        )

    return {"message": "Dispute approved", "refund_status": refund_status, "refund_id": refund_id}


@router.patch("/{dispute_id}/reject")
def reject_dispute(dispute_id: str, current_user=Depends(require_role(["admin"]))):
    if not ObjectId.is_valid(dispute_id):
        raise HTTPException(status_code=400, detail="Invalid dispute_id")

    dispute = disputes_collection.find_one({"_id": ObjectId(dispute_id)})
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute.get("status") != "pending":
        return {"message": "Dispute already processed", "status": dispute.get("status")}

    disputes_collection.update_one(
        {"_id": ObjectId(dispute_id)},
        {"$set": {"status": "rejected", "rejected_at": int(time.time()), "rejected_by": current_user["id"]}},
    )

    # Notify the buyer
    buyer_id = dispute.get("buyer_id")
    note_id = str(dispute.get("note_id", ""))
    if buyer_id:
        notify(
            buyer_id,
            "dispute_rejected",
            "Your dispute has been reviewed and rejected.",
            link=f"/notes/{note_id}" if note_id else None,
        )

    return {"message": "Dispute rejected ✅"}
