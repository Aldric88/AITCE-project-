import time
from bson import ObjectId
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from app.database import (
    notes_collection,
    purchases_collection,
    coupons_collection,
    campaigns_collection,
    pass_subscriptions_collection,
    seller_experiments_collection,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/seller", tags=["Seller Dashboard"])


class CouponABExperimentCreate(BaseModel):
    note_id: str
    title: str = Field(min_length=3, max_length=120)
    variant_a_code: str = Field(min_length=3, max_length=24)
    variant_b_code: str = Field(min_length=3, max_length=24)
    starts_at: int
    ends_at: int

@router.get("/dashboard")
def seller_dashboard(current_user=Depends(get_current_user)):
    # notes uploaded by seller
    my_notes = list(
        notes_collection.find(
            {"uploader_id": ObjectId(current_user["id"])},
            {"title": 1, "subject": 1, "price": 1, "is_paid": 1},
        )
    )

    note_ids = [n["_id"] for n in my_notes]
    if not note_ids:
        return {
            "seller_id": current_user["id"],
            "total_notes": 0,
            "total_sales": 0,
            "total_earnings": 0,
            "top_notes": [],
        }

    sales_by_note = {}
    total_sales = 0
    total_earnings = 0
    for row in purchases_collection.aggregate(
        [
            {"$match": {"note_id": {"$in": note_ids}, "status": "success"}},
            {
                "$group": {
                    "_id": "$note_id",
                    "sales": {"$sum": 1},
                    "earnings": {"$sum": {"$toInt": {"$ifNull": ["$amount", 0]}}},
                }
            },
        ]
    ):
        nid = row["_id"]
        sales = int(row.get("sales", 0))
        earnings = int(row.get("earnings", 0))
        sales_by_note[nid] = {"sales": sales, "earnings": earnings}
        total_sales += sales
        total_earnings += earnings

    top_notes = []
    for n in my_notes:
        note_sales = sales_by_note.get(n["_id"], {}).get("sales", 0)
        top_notes.append({
            "id": str(n["_id"]),
            "title": n.get("title"),
            "subject": n.get("subject"),
            "price": n.get("price", 0),
            "is_paid": n.get("is_paid", False),
            "sales": note_sales
        })

    top_notes = sorted(top_notes, key=lambda x: x["sales"], reverse=True)[:10]

    return {
        "seller_id": current_user["id"],
        "total_notes": len(my_notes),
        "total_sales": total_sales,
        "total_earnings": total_earnings,
        "top_notes": top_notes
    }


@router.get("/funnel")
def seller_funnel(
    days: int = Query(default=30, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    since = int(time.time()) - days * 24 * 3600
    notes = list(
        notes_collection.find(
            {"uploader_id": ObjectId(current_user["id"])},
            {"views": 1, "downloads": 1},
        )
    )
    note_ids = [n["_id"] for n in notes]
    total_views = sum(int(n.get("views", 0)) for n in notes)
    total_downloads = sum(int(n.get("downloads", 0)) for n in notes)
    total_checkouts = 0
    total_purchases = 0
    if note_ids:
        total_checkouts = purchases_collection.count_documents(
            {"note_id": {"$in": note_ids}, "created_at": {"$gte": since}}
        )
        total_purchases = purchases_collection.count_documents(
            {
                "note_id": {"$in": note_ids},
                "status": "success",
                "created_at": {"$gte": since},
            }
        )
    view_to_checkout = round((total_checkouts / total_views), 4) if total_views else 0.0
    checkout_to_purchase = round((total_purchases / total_checkouts), 4) if total_checkouts else 0.0
    return {
        "days": days,
        "views": total_views,
        "checkouts": total_checkouts,
        "purchases": total_purchases,
        "downloads": total_downloads,
        "conversion": {
            "view_to_checkout": view_to_checkout,
            "checkout_to_purchase": checkout_to_purchase,
        },
    }


@router.get("/coupon-performance")
def seller_coupon_performance(
    days: int = Query(default=60, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    since = int(time.time()) - days * 24 * 3600
    my_notes = list(
        notes_collection.find(
            {"uploader_id": ObjectId(current_user["id"])},
            {"_id": 1},
        )
    )
    note_ids = [n["_id"] for n in my_notes]
    coupons = list(coupons_collection.find({"seller_id": ObjectId(current_user["id"])}))
    coupon_map = {c.get("code"): c for c in coupons if c.get("code")}

    performance = {}
    if note_ids:
        for row in purchases_collection.find(
            {
                "note_id": {"$in": note_ids},
                "status": "success",
                "created_at": {"$gte": since},
                "coupon_code": {"$exists": True, "$ne": None},
            },
            {"coupon_code": 1, "amount": 1, "discount_amount": 1},
        ):
            code = str(row.get("coupon_code") or "").strip().upper()
            if not code:
                continue
            entry = performance.setdefault(
                code,
                {"code": code, "orders": 0, "revenue": 0, "discount": 0},
            )
            entry["orders"] += 1
            entry["revenue"] += int(row.get("amount", 0))
            entry["discount"] += int(row.get("discount_amount", 0))

    out = []
    for code, stats in performance.items():
        coupon = coupon_map.get(code) or {}
        out.append(
            {
                "code": code,
                "orders": stats["orders"],
                "revenue": stats["revenue"],
                "discount": stats["discount"],
                "uses_total": int(coupon.get("uses", 0)),
                "max_uses": int(coupon.get("max_uses", 0)) if coupon.get("max_uses") else None,
                "is_active": bool(coupon.get("is_active", False)),
            }
        )
    out.sort(key=lambda r: r["orders"], reverse=True)
    return {"days": days, "coupons": out}


@router.get("/churn-alerts")
def seller_churn_alerts(
    inactivity_days: int = Query(default=30, ge=7, le=365),
    current_user=Depends(get_current_user),
):
    now_ts = int(time.time())
    cutoff = now_ts - inactivity_days * 24 * 3600
    notes = list(
        notes_collection.find(
            {"uploader_id": ObjectId(current_user["id"])},
            {"_id": 1, "title": 1},
        )
    )
    note_ids = [n["_id"] for n in notes]
    if not note_ids:
        return {"inactivity_days": inactivity_days, "alerts": []}

    buyer_last_purchase = {}
    for row in purchases_collection.find(
        {"note_id": {"$in": note_ids}, "status": "success"},
        {"buyer_id": 1, "user_id": 1, "created_at": 1},
    ):
        buyer = row.get("buyer_id") or row.get("user_id")
        if not buyer:
            continue
        ts = int(row.get("created_at", 0))
        prev = buyer_last_purchase.get(buyer, 0)
        if ts > prev:
            buyer_last_purchase[buyer] = ts

    alerts = []
    for buyer, last_ts in buyer_last_purchase.items():
        if last_ts >= cutoff:
            continue
        alerts.append(
            {
                "buyer_id": str(buyer),
                "days_since_last_purchase": int((now_ts - last_ts) / 86400),
                "last_purchase_at": last_ts,
                "suggestion": "Send a comeback coupon or release update notes in buyer's previous subjects.",
            }
        )
    alerts.sort(key=lambda a: a["days_since_last_purchase"], reverse=True)

    active_passes = pass_subscriptions_collection.count_documents(
        {
            "seller_id": ObjectId(current_user["id"]),
            "status": "active",
            "expires_at": {"$gte": now_ts},
        }
    )
    active_campaigns = campaigns_collection.count_documents(
        {
            "seller_id": ObjectId(current_user["id"]),
            "is_active": True,
            "starts_at": {"$lte": now_ts},
            "ends_at": {"$gte": now_ts},
        }
    )
    return {
        "inactivity_days": inactivity_days,
        "active_creator_pass_subscriptions": active_passes,
        "active_campaigns": active_campaigns,
        "alerts": alerts[:100],
    }


@router.post("/experiments/coupon-ab")
def create_coupon_ab_experiment(data: CouponABExperimentCreate, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(data.note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note = notes_collection.find_one({"_id": ObjectId(data.note_id)})
    if not note or str(note.get("uploader_id")) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only owner can run experiments")
    if data.ends_at <= data.starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be greater than starts_at")

    a_code = data.variant_a_code.strip().upper()
    b_code = data.variant_b_code.strip().upper()
    if a_code == b_code:
        raise HTTPException(status_code=400, detail="A/B codes must be different")
    for code in (a_code, b_code):
        coupon = coupons_collection.find_one({"code": code, "seller_id": ObjectId(current_user["id"])})
        if not coupon:
            raise HTTPException(status_code=404, detail=f"Coupon not found for variant code: {code}")

    doc = {
        "seller_id": ObjectId(current_user["id"]),
        "note_id": ObjectId(data.note_id),
        "title": data.title.strip(),
        "variant_a_code": a_code,
        "variant_b_code": b_code,
        "starts_at": int(data.starts_at),
        "ends_at": int(data.ends_at),
        "status": "active",
        "created_at": int(time.time()),
    }
    res = seller_experiments_collection.insert_one(doc)
    return {"id": str(res.inserted_id), "message": "Coupon A/B experiment created ✅"}


@router.get("/experiments/coupon-ab")
def list_coupon_ab_experiments(current_user=Depends(get_current_user)):
    rows = list(
        seller_experiments_collection.find({"seller_id": ObjectId(current_user["id"])}).sort("created_at", -1).limit(50)
    )
    out = []
    for row in rows:
        starts_at = int(row.get("starts_at", 0))
        ends_at = int(row.get("ends_at", 0))
        query = {
            "note_id": row.get("note_id"),
            "status": "success",
            "created_at": {"$gte": starts_at, "$lte": ends_at},
        }
        a_code = row.get("variant_a_code")
        b_code = row.get("variant_b_code")
        a_orders = purchases_collection.count_documents({**query, "coupon_code": a_code})
        b_orders = purchases_collection.count_documents({**query, "coupon_code": b_code})
        out.append(
            {
                "id": str(row["_id"]),
                "title": row.get("title"),
                "note_id": str(row.get("note_id")) if row.get("note_id") else None,
                "variant_a_code": a_code,
                "variant_b_code": b_code,
                "variant_a_orders": a_orders,
                "variant_b_orders": b_orders,
                "winner": "A" if a_orders > b_orders else "B" if b_orders > a_orders else "tie",
                "starts_at": starts_at,
                "ends_at": ends_at,
                "status": row.get("status", "active"),
            }
        )
    return out
