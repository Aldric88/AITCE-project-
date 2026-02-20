import os
import time
import hmac
import hashlib
import logging

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from dotenv import load_dotenv

from app.config import settings
from app.database import (
    notes_collection,
    purchases_collection,
    payment_events_collection,
    payment_webhook_events_collection,
    coupons_collection,
    campaigns_collection,
)
from app.utils.dependencies import get_current_user
from app.utils.idempotency import (
    get_saved_idempotent_response,
    make_request_fingerprint,
    save_idempotent_response,
)
from app.services.ledger_service import add_ledger_entry

load_dotenv()
logger = logging.getLogger(__name__)

try:
    import razorpay
except Exception:  # pragma: no cover
    razorpay = None

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    logger.warning("Razorpay keys missing in environment")

client = (
    razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    if razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET
    else None
)

router = APIRouter(prefix="/payments", tags=["Payments"])


class CreateOrderRequest(BaseModel):
    note_id: str
    coupon_code: str | None = None


class VerifyPaymentRequest(BaseModel):
    note_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def _has_success_purchase(note_id: str, buyer_id: str):
    return purchases_collection.find_one(
        {
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(buyer_id),
            "status": "success",
        }
    )


def _log_payment_event(event_type: str, payload: dict):
    payment_events_collection.insert_one(
        {
            "event_type": event_type,
            "payload": payload,
            "created_at": int(time.time()),
        }
    )


@router.post("/create-order")
def create_order(
    data: CreateOrderRequest,
    x_idempotency_key: str = Header(default=""),
    current_user=Depends(get_current_user),
):
    if client is None:
        raise HTTPException(status_code=503, detail="Payment gateway is not configured")
    if not x_idempotency_key:
        raise HTTPException(status_code=400, detail="X-Idempotency-Key header is required")

    note_id = data.note_id
    route = "/payments/create-order"
    fingerprint = make_request_fingerprint({"note_id": note_id, "coupon_code": data.coupon_code})
    saved = get_saved_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint)
    if saved:
        return saved

    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Note not approved")
    if str(note.get("uploader_id")) == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot purchase your own note")

    if not note.get("is_paid", False):
        raise HTTPException(status_code=400, detail="This is a free note. Payment not required.")

    price = int(note.get("price", 0))
    if price <= 0:
        raise HTTPException(status_code=400, detail="Invalid note price")
    final_price = price
    discount_amount = 0
    applied_coupon = None

    now = int(time.time())
    campaign = None
    try:
        campaign = campaigns_collection.find_one(
            {
                "note_id": note["_id"],
                "is_active": True,
                "starts_at": {"$lte": now},
                "ends_at": {"$gte": now},
            },
            sort=[("discount_percent", -1)],
        )
    except Exception:
        campaign = None
    if campaign:
        campaign_discount = int((price * int(campaign.get("discount_percent", 0))) / 100)
        discount_amount = max(discount_amount, campaign_discount)

    if data.coupon_code:
        coupon = None
        try:
            coupon = coupons_collection.find_one({"code": data.coupon_code.strip().upper(), "is_active": True})
        except Exception:
            coupon = None
        if coupon:
            if (not coupon.get("expires_at") or int(coupon.get("expires_at")) >= now) and int(coupon.get("uses", 0)) < int(coupon.get("max_uses", 0)):
                if (not coupon.get("note_id")) or coupon.get("note_id") == note["_id"]:
                    coupon_discount = int((price * int(coupon.get("percent_off", 0))) / 100)
                    if coupon_discount >= discount_amount:
                        discount_amount = coupon_discount
                        applied_coupon = coupon

    final_price = max(price - discount_amount, 1)
    amount_paise = final_price * 100

    existing = _has_success_purchase(note_id, current_user["id"])

    if existing:
        response = {"message": "Already purchased ✅"}
        save_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint, response)
        return response

    pending = purchases_collection.find_one(
        {
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(current_user["id"]),
            "status": "pending",
            "amount": final_price,
        },
        sort=[("created_at", -1)],
    )
    if pending and pending.get("razorpay_order_id"):
        response = {
            "order_id": pending["razorpay_order_id"],
            "amount": amount_paise,
            "currency": "INR",
            "key_id": RAZORPAY_KEY_ID,
            "note_title": note.get("title"),
            "user_email": current_user["email"],
            "user_name": current_user["name"],
            "reused_pending_order": True,
            "discount_amount": discount_amount,
            "final_amount": final_price,
        }
        save_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint, response)
        return response

    receipt_id = f"rcpt_{note_id}_{current_user['id']}_{int(time.time())}"

    order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt_id,
        "payment_capture": 1
    })

    purchases_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(current_user["id"]),
            "user_id": ObjectId(current_user["id"]),
            "amount": final_price,
            "original_amount": price,
            "discount_amount": discount_amount,
            "coupon_code": applied_coupon.get("code") if applied_coupon else None,
            "status": "pending",
            "purchase_type": "razorpay",
            "razorpay_order_id": order["id"],
            "created_at": int(time.time()),
        }
    )

    response = {
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID,
        "note_title": note.get("title"),
        "user_email": current_user["email"],
        "user_name": current_user["name"],
        "discount_amount": discount_amount,
        "final_amount": final_price,
        "coupon_code": applied_coupon.get("code") if applied_coupon else None,
    }
    if applied_coupon:
        try:
            coupons_collection.update_one({"_id": applied_coupon["_id"]}, {"$inc": {"uses": 1}})
        except Exception:
            pass
    save_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint, response)
    return response


@router.post("/verify")
def verify_payment(
    data: VerifyPaymentRequest,
    x_idempotency_key: str = Header(default=""),
    current_user=Depends(get_current_user),
):
    if client is None:
        raise HTTPException(status_code=503, detail="Payment gateway is not configured")
    if not x_idempotency_key:
        raise HTTPException(status_code=400, detail="X-Idempotency-Key header is required")

    note_id = data.note_id
    route = "/payments/verify"
    fingerprint = make_request_fingerprint(data.model_dump())
    saved = get_saved_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint)
    if saved:
        return saved

    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    already_success = _has_success_purchase(note_id, current_user["id"])
    if already_success:
        existing_payment_id = already_success.get("razorpay_payment_id")
        if existing_payment_id and existing_payment_id != data.razorpay_payment_id:
            raise HTTPException(status_code=409, detail="Order already completed with different payment id")
        response = {"message": "Payment already verified ✅", "idempotent": True}
        save_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint, response)
        return response

    pending = purchases_collection.find_one(
        {
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(current_user["id"]),
            "status": "pending",
            "razorpay_order_id": data.razorpay_order_id,
        }
    )

    if not pending:
        raise HTTPException(status_code=404, detail="Pending purchase not found")

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "razorpay_signature": data.razorpay_signature
        })
    except Exception as exc:
        purchases_collection.update_one(
            {"_id": pending["_id"]},
            {"$set": {"status": "failed"}}
        )
        _log_payment_event(
            "verify_failed",
            {
                "note_id": note_id,
                "buyer_id": current_user["id"],
                "order_id": data.razorpay_order_id,
                "payment_id": data.razorpay_payment_id,
                "error": str(exc),
            },
        )
        raise HTTPException(status_code=400, detail="Payment verification failed ❌")

    purchases_collection.update_one(
        {"_id": pending["_id"]},
        {"$set": {
            "status": "success",
            "razorpay_payment_id": data.razorpay_payment_id,
            "razorpay_signature": data.razorpay_signature,
            "verified_at": int(time.time()),
            "purchase_type": "razorpay",
        }}
    )
    _log_payment_event(
        "verify_success",
        {
            "note_id": note_id,
            "buyer_id": current_user["id"],
            "order_id": data.razorpay_order_id,
            "payment_id": data.razorpay_payment_id,
        },
    )
    note = notes_collection.find_one({"_id": pending["note_id"]})
    if note:
        add_ledger_entry(
            purchase_id=pending["_id"],
            buyer_id=pending["buyer_id"],
            seller_id=note["uploader_id"],
            note_id=pending["note_id"],
            amount=int(pending.get("amount", 0)),
            currency="INR",
            entry_type="purchase_success",
            source="payments.verify",
            metadata={
                "razorpay_order_id": data.razorpay_order_id,
                "razorpay_payment_id": data.razorpay_payment_id,
            },
        )
    response = {"message": "Payment verified ✅ Purchase successful"}
    save_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint, response)
    return response


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
):
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    raw_body = await request.body()
    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, x_razorpay_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    data = await request.json()
    event_id = data.get("id")
    if not event_id:
        raise HTTPException(status_code=400, detail="Webhook event id missing")

    existing_event = payment_webhook_events_collection.find_one({"event_id": event_id})
    if existing_event:
        return {"message": "Duplicate webhook ignored", "idempotent": True}

    payment_webhook_events_collection.insert_one(
        {
            "event_id": event_id,
            "event": data.get("event"),
            "received_at": int(time.time()),
        }
    )

    event_type = data.get("event")
    payment_entity = data.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")
    amount = int(payment_entity.get("amount", 0)) // 100 if payment_entity.get("amount") else None

    if event_type not in {"payment.captured", "order.paid"}:
        _log_payment_event("webhook_ignored", {"event_id": event_id, "event": event_type})
        return {"message": "Webhook received", "processed": False}

    if not order_id:
        _log_payment_event("webhook_missing_order", {"event_id": event_id, "event": event_type})
        return {"message": "Webhook received", "processed": False}

    purchase = purchases_collection.find_one({"razorpay_order_id": order_id})
    if not purchase:
        _log_payment_event(
            "webhook_unmatched_order",
            {"event_id": event_id, "event": event_type, "order_id": order_id, "payment_id": payment_id},
        )
        return {"message": "Webhook received", "processed": False}

    if purchase.get("status") == "success":
        _log_payment_event(
            "webhook_already_success",
            {"event_id": event_id, "order_id": order_id, "payment_id": payment_id},
        )
        return {"message": "Already settled", "processed": True, "idempotent": True}

    purchases_collection.update_one(
        {"_id": purchase["_id"]},
        {
            "$set": {
                "status": "success",
                "purchase_type": "razorpay",
                "razorpay_payment_id": payment_id,
                "verified_at": int(time.time()),
            }
        },
    )
    _log_payment_event(
        "webhook_settled",
        {
            "event_id": event_id,
            "order_id": order_id,
            "payment_id": payment_id,
            "amount": amount,
            "purchase_id": str(purchase["_id"]),
        },
    )
    note = notes_collection.find_one({"_id": purchase["note_id"]})
    if note:
        add_ledger_entry(
            purchase_id=purchase["_id"],
            buyer_id=purchase["buyer_id"],
            seller_id=note["uploader_id"],
            note_id=purchase["note_id"],
            amount=int(purchase.get("amount", 0)),
            currency="INR",
            entry_type="purchase_success",
            source="payments.webhook",
            metadata={"event_id": event_id, "order_id": order_id, "payment_id": payment_id},
        )
    return {"message": "Webhook processed", "processed": True}
