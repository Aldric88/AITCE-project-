import time
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from pydantic import BaseModel
from app.database import purchases_collection, notes_collection
from app.utils.dependencies import get_current_user
from app.utils.idempotency import (
    make_request_fingerprint,
    get_saved_idempotent_response,
    save_idempotent_response,
)
from app.services.ledger_service import add_ledger_entry
from app.services.purchase_service import purchase_query, list_user_purchase_rows
from app.services.pass_service import has_active_creator_pass
from app.services.points_service import spend_points, award_points, get_wallet_balance
from app.config import settings

router = APIRouter(prefix="/purchase", tags=["Purchase"])
router_plural = APIRouter(prefix="/purchases", tags=["Purchase"])
router_library = APIRouter(prefix="/library", tags=["Purchase"])


class PurchaseRequest(BaseModel):
    payment_method: str | None = "free"


def _purchase_query(user_id: str, note_id: str):
    return purchase_query(user_id=user_id, note_id=note_id)


@router.post("/{note_id}")
def buy_note(
    note_id: str,
    data: PurchaseRequest | None = Body(default=None),
    x_idempotency_key: str = Header(default=""),
    current_user=Depends(get_current_user),
):
    if not x_idempotency_key:
        raise HTTPException(status_code=400, detail="X-Idempotency-Key header is required")

    route = f"/purchase/{note_id}"
    payment_method = ((data.payment_method if data else "free") or "free").strip().lower()
    fingerprint = make_request_fingerprint({"note_id": note_id, "payment_method": payment_method})
    saved = get_saved_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint)
    if saved:
        return saved

    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")

    note = notes_collection.find_one({"_id": ObjectId(note_id), "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if str(note.get("uploader_id")) == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot purchase your own note")

    # already purchased?
    existing = purchases_collection.find_one(_purchase_query(current_user["id"], note_id))
    if existing:
        response = {"message": "Already unlocked ✅"}
        save_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint, response)
        return response

    note_price = int(note.get("price", 0))
    is_paid = note.get("is_paid", False)

    # ── Points purchase ───────────────────────────────────────────────────────
    if payment_method == "points" and is_paid:
        if note_price <= 0:
            raise HTTPException(status_code=400, detail="Note price is invalid")
        deducted = spend_points(
            user_id=current_user["id"],
            points=note_price,
            reason="note_purchase_points",
            meta={"note_id": note_id},
        )
        if not deducted:
            raise HTTPException(status_code=400, detail=f"Insufficient points. You need {note_price} pts to unlock this note.")

        result = purchases_collection.insert_one({
            "buyer_id": ObjectId(current_user["id"]),
            "user_id": ObjectId(current_user["id"]),
            "note_id": ObjectId(note_id),
            "amount": note_price,
            "status": "success",
            "purchase_type": "points",
            "created_at": int(time.time()),
        })
        add_ledger_entry(
            purchase_id=result.inserted_id,
            buyer_id=ObjectId(current_user["id"]),
            seller_id=note["uploader_id"],
            note_id=ObjectId(note_id),
            amount=note_price,
            currency="PTS",
            entry_type="points_purchase",
            source="purchase.points",
        )
        # Award seller a share of points (50%)
        seller_share = max(1, note_price // 2)
        try:
            award_points(
                user_id=note["uploader_id"],
                points=seller_share,
                reason="note_sold_points",
                meta={"note_id": note_id, "buyer_id": current_user["id"]},
            )
        except Exception:
            pass  # non-critical: don't fail the purchase if seller credit fails

        response = {"message": f"Note unlocked with {note_price} points ✅", "paid": True, "payment_method": "points"}
        save_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint, response)
        return response

    # ── Free unlock (free notes or payment_method != "points") ────────────────
    if is_paid and payment_method != "points":
        raise HTTPException(status_code=400, detail="This is a paid note. Use points or complete INR payment.")

    result = purchases_collection.insert_one({
        "buyer_id": ObjectId(current_user["id"]),
        "user_id": ObjectId(current_user["id"]),
        "note_id": ObjectId(note_id),
        "amount": 0,
        "status": "success",
        "purchase_type": "free",
        "created_at": int(time.time()),
    })
    add_ledger_entry(
        purchase_id=result.inserted_id,
        buyer_id=ObjectId(current_user["id"]),
        seller_id=note["uploader_id"],
        note_id=ObjectId(note_id),
        amount=0,
        currency="INR",
        entry_type="free_unlock",
        source="purchase.free",
    )
    response = {"message": "Note unlocked ✅", "paid": False}
    save_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint, response)
    return response


@router.get("/my")
def my_purchases(current_user=Depends(get_current_user)):
    return list_user_purchase_rows(
        user_id=current_user["id"],
        purchases_collection=purchases_collection,
        notes_collection=notes_collection,
    )


@router.get("/has/{note_id}")
def has_access(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")

    existing = purchases_collection.find_one(_purchase_query(current_user["id"], note_id))
    if existing:
        return {"has_access": True}
    note = notes_collection.find_one({"_id": ObjectId(note_id)}, {"uploader_id": 1})
    if not note:
        return {"has_access": False}
    return {"has_access": has_active_creator_pass(current_user["id"], note.get("uploader_id"))}


@router_plural.post("/{note_id}")
def buy_note_plural_alias(
    note_id: str,
    data: PurchaseRequest | None = Body(default=None),
    x_idempotency_key: str = Header(default=""),
    current_user=Depends(get_current_user),
):
    return buy_note(
        note_id=note_id,
        data=data,
        x_idempotency_key=x_idempotency_key,
        current_user=current_user,
    )


@router_plural.get("/my")
def my_purchases_plural_alias(current_user=Depends(get_current_user)):
    return my_purchases(current_user=current_user)


@router_plural.get("/has/{note_id}")
def has_access_plural_alias(note_id: str, current_user=Depends(get_current_user)):
    return has_access(note_id=note_id, current_user=current_user)


@router_library.get("/my")
def my_library(current_user=Depends(get_current_user)):
    rows = my_purchases(current_user=current_user)
    out = []
    for row in rows:
        note = row.get("note") or {}
        out.append(
            {
                "purchase_id": row.get("purchase_id"),
                "note_id": row.get("note_id"),
                "title": note.get("title", "Untitled"),
                "subject": note.get("subject", ""),
                "unit": note.get("unit"),
                "semester": note.get("semester"),
                "dept": note.get("dept"),
                "description": note.get("description"),
                "is_paid": note.get("is_paid", False),
                "price": note.get("price", row.get("amount", 0)),
                "unlocked_type": row.get("unlocked_type"),
                "unlocked_at": row.get("unlocked_at"),
            }
        )
    return out
