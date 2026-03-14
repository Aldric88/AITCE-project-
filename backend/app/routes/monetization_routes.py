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
    creator_passes_collection,
    pass_subscriptions_collection,
    users_collection,
)
from app.utils.dependencies import get_current_user, require_role
from app.services.points_service import spend_points, award_points, get_wallet_balance

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


class CreatorPassCreate(BaseModel):
    title: str = Field(min_length=3, max_length=80)
    description: str = Field(default="", max_length=500)
    monthly_price: int = Field(ge=1, le=5000)
    duration_days: int = Field(default=30, ge=7, le=365)
    max_subscribers: Optional[int] = Field(default=None, ge=1, le=50000)


class SubscribePassRequest(BaseModel):
    payment_method: str = Field(default="points")


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
    now_ts = int(time.time())
    for r in rows:
        status = "active"
        if not r.get("is_active", True):
            status = "disabled"
        elif r.get("expires_at") and int(r.get("expires_at", 0)) < now_ts:
            status = "expired"
        elif int(r.get("uses", 0)) >= int(r.get("max_uses", 0)):
            status = "exhausted"
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
                "status": status,
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
    now_ts = int(time.time())
    for r in rows:
        if not r.get("is_active", True):
            status = "disabled"
        elif int(r.get("starts_at", 0)) > now_ts:
            status = "draft"
        elif int(r.get("ends_at", 0)) < now_ts:
            status = "expired"
        else:
            status = "active"
        out.append(
            {
                "id": str(r["_id"]),
                "note_id": str(r.get("note_id")),
                "title": r.get("title"),
                "discount_percent": r.get("discount_percent"),
                "starts_at": r.get("starts_at"),
                "ends_at": r.get("ends_at"),
                "is_active": r.get("is_active", True),
                "status": status,
            }
        )
    return out


@router.get("/payouts/me")
def payout_history_me(current_user=Depends(get_current_user)):
    rows = list(
        ledger_entries_collection.find(
            {
                "seller_id": ObjectId(current_user["id"]),
                "entry_type": {"$in": ["purchase_success", "free_unlock", "points_purchase", "creator_pass_subscription", "refund"]},
            }
        ).sort("created_at", -1).limit(200)
    )
    total_inr = 0
    total_points = 0
    out = []
    for r in rows:
        amount = int(r.get("amount", 0))
        currency = str(r.get("currency", "INR")).upper()
        if currency == "POINTS":
            total_points += amount
        else:
            total_inr += amount
        out.append(
            {
                "id": str(r["_id"]),
                "purchase_id": str(r.get("purchase_id")) if r.get("purchase_id") else None,
                "note_id": str(r.get("note_id")) if r.get("note_id") else None,
                "amount": amount,
                "currency": currency,
                "entry_type": r.get("entry_type"),
                "created_at": r.get("created_at"),
            }
        )
    return {
        "total_earned_inr": total_inr,
        "total_earned_points": total_points,
        "entries": out,
    }


@router.post("/passes")
def create_creator_pass(data: CreatorPassCreate, current_user=Depends(get_current_user)):
    if not _is_seller_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Only sellers/admin can create creator passes")
    doc = {
        "seller_id": ObjectId(current_user["id"]),
        "title": data.title.strip(),
        "description": data.description.strip(),
        "monthly_price": int(data.monthly_price),
        "duration_days": int(data.duration_days),
        "max_subscribers": int(data.max_subscribers) if data.max_subscribers else None,
        "is_active": True,
        "created_at": int(time.time()),
    }
    res = creator_passes_collection.insert_one(doc)
    return {"id": str(res.inserted_id), "message": "Creator pass created ✅"}


def _batch_active_subscriber_counts(pass_ids: list, now_ts: int) -> dict:
    """Return {pass_id: active_count} for all given pass_ids in a single aggregation."""
    if not pass_ids:
        return {}
    pipeline = [
        {"$match": {"pass_id": {"$in": pass_ids}, "status": "active", "expires_at": {"$gte": now_ts}}},
        {"$group": {"_id": "$pass_id", "count": {"$sum": 1}}},
    ]
    return {r["_id"]: r["count"] for r in pass_subscriptions_collection.aggregate(pipeline)}


@router.get("/passes/my")
def my_creator_passes(current_user=Depends(get_current_user)):
    rows = list(
        creator_passes_collection.find({"seller_id": ObjectId(current_user["id"])}).sort("created_at", -1)
    )
    now_ts = int(time.time())
    counts = _batch_active_subscriber_counts([r["_id"] for r in rows], now_ts)
    return [
        {
            "id": str(row["_id"]),
            "title": row.get("title"),
            "description": row.get("description", ""),
            "monthly_price": int(row.get("monthly_price", 0)),
            "duration_days": int(row.get("duration_days", 30)),
            "max_subscribers": row.get("max_subscribers"),
            "is_active": bool(row.get("is_active", True)),
            "active_subscriptions": counts.get(row["_id"], 0),
        }
        for row in rows
    ]


@router.get("/passes/available")
def list_available_passes(current_user=Depends(get_current_user)):
    rows = list(creator_passes_collection.find({"is_active": True}).sort("created_at", -1).limit(100))
    seller_ids = [row.get("seller_id") for row in rows if row.get("seller_id")]
    users = {}
    if seller_ids:
        for u in users_collection.find({"_id": {"$in": seller_ids}}, {"name": 1}):
            users[u["_id"]] = u.get("name", "Creator")

    now_ts = int(time.time())
    visible = [r for r in rows if str(r.get("seller_id")) != current_user["id"]]
    counts = _batch_active_subscriber_counts([r["_id"] for r in visible], now_ts)
    return [
        {
            "id": str(row["_id"]),
            "seller_id": str(row.get("seller_id")),
            "seller_name": users.get(row.get("seller_id"), "Creator"),
            "title": row.get("title"),
            "description": row.get("description", ""),
            "monthly_price": int(row.get("monthly_price", 0)),
            "duration_days": int(row.get("duration_days", 30)),
            "max_subscribers": row.get("max_subscribers"),
            "active_subscriptions": counts.get(row["_id"], 0),
        }
        for row in visible
    ]


@router.post("/passes/{pass_id}/subscribe")
def subscribe_creator_pass(
    pass_id: str,
    data: SubscribePassRequest,
    current_user=Depends(get_current_user),
):
    if not ObjectId.is_valid(pass_id):
        raise HTTPException(status_code=400, detail="Invalid pass id")
    pass_doc = creator_passes_collection.find_one({"_id": ObjectId(pass_id), "is_active": True})
    if not pass_doc:
        raise HTTPException(status_code=404, detail="Creator pass not found")
    if str(pass_doc.get("seller_id")) == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot subscribe to your own pass")

    now_ts = int(time.time())
    existing = pass_subscriptions_collection.find_one(
        {
            "pass_id": pass_doc["_id"],
            "buyer_id": ObjectId(current_user["id"]),
            "status": "active",
            "expires_at": {"$gte": now_ts},
        }
    )
    if existing:
        return {
            "message": "Already subscribed ✅",
            "subscription_id": str(existing["_id"]),
            "expires_at": existing.get("expires_at"),
        }

    payment_method = (data.payment_method or "points").strip().lower()
    if payment_method != "points":
        raise HTTPException(status_code=400, detail="Only points payment is supported for creator pass in this build")

    max_subscribers = pass_doc.get("max_subscribers")
    if max_subscribers:
        active_count = pass_subscriptions_collection.count_documents(
            {
                "pass_id": pass_doc["_id"],
                "status": "active",
                "expires_at": {"$gte": now_ts},
            }
        )
        if active_count >= int(max_subscribers):
            raise HTTPException(status_code=400, detail="Creator pass has reached subscriber limit")

    expires_at = now_ts + int(pass_doc.get("duration_days", 30)) * 24 * 3600
    price = int(pass_doc.get("monthly_price", 0))
    spent = spend_points(
        user_id=current_user["id"],
        points=price,
        reason="creator_pass_purchase_points_debit",
        meta={"pass_id": pass_id},
    )
    if not spent:
        raise HTTPException(status_code=400, detail="Not enough wallet points")
    sub_doc = {
        "pass_id": pass_doc["_id"],
        "seller_id": pass_doc["seller_id"],
        "buyer_id": ObjectId(current_user["id"]),
        "status": "active",
        "price_paid": price,
        "purchase_type": "points",
        "started_at": now_ts,
        "expires_at": expires_at,
        "created_at": now_ts,
    }
    res = pass_subscriptions_collection.insert_one(sub_doc)

    ledger_entries_collection.insert_one(
        {
            "purchase_id": None,
            "buyer_id": ObjectId(current_user["id"]),
            "seller_id": pass_doc["seller_id"],
            "note_id": None,
            "amount": price,
            "currency": "POINTS",
            "entry_type": "creator_pass_subscription",
            "source": "monetization.pass",
            "metadata": {"payment_method": "points"},
            "created_at": now_ts,
        }
    )
    seller_reward = int(price * 0.8)
    if seller_reward > 0:
        award_points(
            user_id=pass_doc["seller_id"],
            points=seller_reward,
            reason="creator_pass_sale_points_credit",
            meta={"pass_id": pass_id, "subscription_id": str(res.inserted_id)},
        )

    seller_doc = users_collection.find_one({"_id": pass_doc["seller_id"]}, {"name": 1})
    return {
        "message": "Creator pass subscription active ✅",
        "subscription_id": str(res.inserted_id),
        "pass_id": pass_id,
        "pass_title": pass_doc.get("title", ""),
        "seller_name": (seller_doc or {}).get("name", "Creator"),
        "expires_at": expires_at,
        "wallet_points": get_wallet_balance(current_user["id"]),
        "spent_points": price,
    }


@router.get("/passes/subscriptions/me")
def my_pass_subscriptions(current_user=Depends(get_current_user)):
    rows = list(
        pass_subscriptions_collection.find({"buyer_id": ObjectId(current_user["id"])}).sort("created_at", -1).limit(200)
    )
    pass_ids = [r.get("pass_id") for r in rows if r.get("pass_id")]
    pass_map = {}
    if pass_ids:
        for p in creator_passes_collection.find({"_id": {"$in": pass_ids}}):
            pass_map[p["_id"]] = p
    seller_ids = [r.get("seller_id") for r in rows if r.get("seller_id")]
    user_map = {}
    if seller_ids:
        for u in users_collection.find({"_id": {"$in": seller_ids}}, {"name": 1}):
            user_map[u["_id"]] = u.get("name", "Creator")

    out = []
    now_ts = int(time.time())
    for row in rows:
        p = pass_map.get(row.get("pass_id"), {})
        out.append(
            {
                "id": str(row["_id"]),
                "pass_id": str(row.get("pass_id")) if row.get("pass_id") else None,
                "seller_id": str(row.get("seller_id")) if row.get("seller_id") else None,
                "seller_name": user_map.get(row.get("seller_id"), "Creator"),
                "title": p.get("title", "Creator Pass"),
                "status": row.get("status"),
                "price_paid": int(row.get("price_paid", 0)),
                "started_at": row.get("started_at"),
                "expires_at": row.get("expires_at"),
                "is_active": row.get("status") == "active" and int(row.get("expires_at", 0)) >= now_ts,
            }
        )
    return out
