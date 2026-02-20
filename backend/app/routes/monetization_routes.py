import time
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import (
    coupons_collection,
    campaigns_collection,
    notes_collection,
    ledger_entries_collection,
)
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/monetization", tags=["Monetization"])


class CouponCreate(BaseModel):
    code: str = Field(min_length=3, max_length=24)
    percent_off: int = Field(ge=1, le=90)
    max_uses: int = Field(default=100, ge=1, le=100000)
    note_id: Optional[str] = None
    expires_at: Optional[int] = None


class ApplyCouponRequest(BaseModel):
    note_id: str
    code: str


class CampaignCreate(BaseModel):
    note_id: str
    title: str = Field(min_length=3, max_length=120)
    discount_percent: int = Field(ge=1, le=90)
    starts_at: int
    ends_at: int


def _is_seller_or_admin(user: dict):
    return user.get("verified_seller") is True or user.get("role") == "admin"


@router.post("/coupons")
def create_coupon(data: CouponCreate, current_user=Depends(get_current_user)):
    if not _is_seller_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Only sellers/admin can create coupons")
    note_oid = None
    if data.note_id:
        if not ObjectId.is_valid(data.note_id):
            raise HTTPException(status_code=400, detail="Invalid note_id")
        note_oid = ObjectId(data.note_id)
        note = notes_collection.find_one({"_id": note_oid})
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        if str(note.get("uploader_id")) != current_user["id"] and current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Only owner can attach coupon to note")

    code = data.code.strip().upper()
    doc = {
        "code": code,
        "seller_id": ObjectId(current_user["id"]),
        "percent_off": data.percent_off,
        "max_uses": data.max_uses,
        "uses": 0,
        "note_id": note_oid,
        "expires_at": data.expires_at,
        "is_active": True,
        "created_at": int(time.time()),
    }
    try:
        res = coupons_collection.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=409, detail="Coupon code already exists")
    return {"id": str(res.inserted_id), "code": code, "message": "Coupon created ✅"}


@router.get("/coupons/my")
def my_coupons(current_user=Depends(get_current_user)):
    rows = list(coupons_collection.find({"seller_id": ObjectId(current_user["id"])}).sort("created_at", -1))
    out = []
    for r in rows:
        out.append(
            {
                "id": str(r["_id"]),
                "code": r.get("code"),
                "percent_off": r.get("percent_off"),
                "max_uses": r.get("max_uses"),
                "uses": r.get("uses", 0),
                "note_id": str(r.get("note_id")) if r.get("note_id") else None,
                "expires_at": r.get("expires_at"),
                "is_active": r.get("is_active", True),
            }
        )
    return out


@router.post("/coupons/apply")
def apply_coupon(data: ApplyCouponRequest, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(data.note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note = notes_collection.find_one({"_id": ObjectId(data.note_id), "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not note.get("is_paid", False):
        return {"valid": False, "detail": "Coupon not needed for free note"}
    code = data.code.strip().upper()
    now = int(time.time())
    coupon = coupons_collection.find_one({"code": code, "is_active": True})
    if not coupon:
        return {"valid": False, "detail": "Coupon not found"}
    if coupon.get("expires_at") and int(coupon["expires_at"]) < now:
        return {"valid": False, "detail": "Coupon expired"}
    if int(coupon.get("uses", 0)) >= int(coupon.get("max_uses", 0)):
        return {"valid": False, "detail": "Coupon usage limit reached"}
    if coupon.get("note_id") and coupon.get("note_id") != note["_id"]:
        return {"valid": False, "detail": "Coupon not applicable for this note"}

    price = int(note.get("price", 0))
    discount = int((price * int(coupon.get("percent_off", 0))) / 100)
    final_amount = max(price - discount, 1)
    return {
        "valid": True,
        "code": code,
        "original_amount": price,
        "discount_amount": discount,
        "final_amount": final_amount,
        "percent_off": coupon.get("percent_off", 0),
    }


@router.post("/campaigns")
def create_campaign(data: CampaignCreate, current_user=Depends(get_current_user)):
    if not _is_seller_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Only sellers/admin can create campaigns")
    if not ObjectId.is_valid(data.note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note = notes_collection.find_one({"_id": ObjectId(data.note_id), "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if str(note.get("uploader_id")) != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only owner can create campaign")
    if data.ends_at <= data.starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    doc = {
        "note_id": note["_id"],
        "seller_id": ObjectId(current_user["id"]),
        "title": data.title.strip(),
        "discount_percent": data.discount_percent,
        "starts_at": data.starts_at,
        "ends_at": data.ends_at,
        "is_active": True,
        "created_at": int(time.time()),
    }
    res = campaigns_collection.insert_one(doc)
    return {"id": str(res.inserted_id), "message": "Campaign created ✅"}


@router.get("/campaigns/my")
def my_campaigns(current_user=Depends(get_current_user)):
    rows = list(campaigns_collection.find({"seller_id": ObjectId(current_user["id"])}).sort("created_at", -1))
    out = []
    for r in rows:
        out.append(
            {
                "id": str(r["_id"]),
                "note_id": str(r.get("note_id")),
                "title": r.get("title"),
                "discount_percent": r.get("discount_percent"),
                "starts_at": r.get("starts_at"),
                "ends_at": r.get("ends_at"),
                "is_active": r.get("is_active", True),
            }
        )
    return out


@router.get("/payouts/me")
def payout_history_me(current_user=Depends(get_current_user)):
    rows = list(
        ledger_entries_collection.find(
            {
                "seller_id": ObjectId(current_user["id"]),
                "entry_type": {"$in": ["purchase_success", "free_unlock"]},
            }
        ).sort("created_at", -1).limit(200)
    )
    total = 0
    out = []
    for r in rows:
        amount = int(r.get("amount", 0))
        total += amount
        out.append(
            {
                "id": str(r["_id"]),
                "purchase_id": str(r.get("purchase_id")) if r.get("purchase_id") else None,
                "note_id": str(r.get("note_id")) if r.get("note_id") else None,
                "amount": amount,
                "currency": r.get("currency", "INR"),
                "entry_type": r.get("entry_type"),
                "created_at": r.get("created_at"),
            }
        )
    return {"total_earned": total, "entries": out}
