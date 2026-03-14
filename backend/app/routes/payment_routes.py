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


def _is_pending_expired(purchase: dict, now_ts: int) -> bool:
    created_at = int(purchase.get("created_at", 0))
    return created_at > 0 and created_at + int(settings.PAYMENT_PENDING_TTL_SECONDS) < now_ts


def _consume_coupon_usage_for_purchase(purchase: dict):
    code = str(purchase.get("coupon_code") or "").strip().upper()
    if not code:
        return
    updated = purchases_collection.update_one(
        {"_id": purchase["_id"], "coupon_consumed": {"$ne": True}},
        {"$set": {"coupon_consumed": True, "coupon_consumed_at": int(time.time())}},
    )
    if getattr(updated, "modified_count", 0) <= 0:
        return
    try:
        coupons_collection.update_one({"code": code, "is_active": True}, {"$inc": {"uses": 1}})
    except Exception:
        logger.exception("Failed to consume coupon usage for purchase_id=%s", purchase.get("_id"))


def _validate_payment_amount_and_order(pending: dict, payment_id: str, order_id: str):
    if not hasattr(client, "payment"):
        return
    try:
        payment = client.payment.fetch(payment_id)
    except Exception as exc:  # pragma: no cover - depends on external API availability
        raise HTTPException(status_code=400, detail=f"Unable to fetch payment details: {exc}")

    fetched_order_id = payment.get("order_id")
    if fetched_order_id != order_id:
        raise HTTPException(status_code=400, detail="Payment order mismatch")

    expected_paise = int(pending.get("amount", 0)) * 100
    paid_paise = int(payment.get("amount", 0))
    if expected_paise != paid_paise:
        raise HTTPException(status_code=400, detail="Payment amount mismatch")
    if str(payment.get("currency", "")).upper() != "INR":
        raise HTTPException(status_code=400, detail="Invalid payment currency")


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
    if pending and _is_pending_expired(pending, now):
        purchases_collection.update_one({"_id": pending["_id"]}, {"$set": {"status": "expired", "expired_at": now}})
        pending = None

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
            "coupon_consumed": False,
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
    if _is_pending_expired(pending, int(time.time())):
        purchases_collection.update_one(
            {"_id": pending["_id"]},
            {"$set": {"status": "expired", "expired_at": int(time.time())}},
        )
        raise HTTPException(status_code=409, detail="Pending purchase expired. Create a new order.")

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "razorpay_signature": data.razorpay_signature
        })
        _validate_payment_amount_and_order(
            pending=pending,
            payment_id=data.razorpay_payment_id,
            order_id=data.razorpay_order_id,
        )
    except HTTPException as exc:
        purchases_collection.update_one(
            {"_id": pending["_id"]},
            {"$set": {"status": "failed"}},
        )
        _log_payment_event(
            "verify_failed",
            {
                "note_id": note_id,
                "buyer_id": current_user["id"],
                "order_id": data.razorpay_order_id,
                "payment_id": data.razorpay_payment_id,
                "error": exc.detail,
            },
        )
        raise
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
    _consume_coupon_usage_for_purchase(pending)
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


class MockCheckoutRequest(BaseModel):
    note_id: str
    coupon_code: str | None = None


@router.post("/mock-checkout")
def mock_checkout(
    data: MockCheckoutRequest,
    x_idempotency_key: str = Header(default=""),
    current_user=Depends(get_current_user),
):
    """
    Mock payment endpoint for demo/resume purposes.
    Simulates a successful INR payment without Razorpay.
    """
    if not x_idempotency_key:
        raise HTTPException(status_code=400, detail="X-Idempotency-Key header is required")

    note_id = data.note_id
    route = "/payments/mock-checkout"
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
        raise HTTPException(status_code=400, detail="Use the free unlock endpoint for free notes")

    # Already purchased?
    existing = _has_success_purchase(note_id, current_user["id"])
    if existing:
        response = {"message": "Already purchased ✅", "mock": True}
        save_idempotent_response(route, current_user["id"], x_idempotency_key, fingerprint, response)
        return response

    price = int(note.get("price", 0))
    now = int(time.time())

    # Apply campaign discount if any
    discount_amount = 0
    applied_coupon = None
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
        if campaign:
            discount_amount = int((price * int(campaign.get("discount_percent", 0))) / 100)
    except Exception:
        pass

    if data.coupon_code:
        try:
            coupon = coupons_collection.find_one({"code": data.coupon_code.strip().upper(), "is_active": True})
            if coupon and (not coupon.get("expires_at") or int(coupon.get("expires_at")) >= now):
                if int(coupon.get("uses", 0)) < int(coupon.get("max_uses", 1)):
                    coupon_discount = int((price * int(coupon.get("percent_off", 0))) / 100)
                    if coupon_discount >= discount_amount:
                        discount_amount = coupon_discount
                        applied_coupon = coupon
        except Exception:
            pass

    final_price = max(price - discount_amount, 1)
    mock_payment_id = f"mock_pay_{current_user['id']}_{note_id}_{now}"
    mock_order_id = f"mock_order_{current_user['id']}_{note_id}_{now}"

    result = purchases_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(current_user["id"]),
            "user_id": ObjectId(current_user["id"]),
            "amount": final_price,
            "original_amount": price,
            "discount_amount": discount_amount,
            "coupon_code": applied_coupon.get("code") if applied_coupon else None,
            "status": "success",
            "purchase_type": "mock_inr",
            "mock_payment_id": mock_payment_id,
            "mock_order_id": mock_order_id,
            "created_at": now,
            "verified_at": now,
            "coupon_consumed": False,
        }
    )

    _log_payment_event(
        "mock_checkout_success",
        {
            "note_id": note_id,
            "buyer_id": current_user["id"],
            "amount": final_price,
            "mock_payment_id": mock_payment_id,
        },
    )

    if applied_coupon:
        try:
            coupons_collection.update_one(
                {"code": applied_coupon["code"], "is_active": True},
                {"$inc": {"uses": 1}},
            )
            purchases_collection.update_one(
                {"_id": result.inserted_id},
                {"$set": {"coupon_consumed": True, "coupon_consumed_at": now}},
            )
        except Exception:
            pass

    add_ledger_entry(
        purchase_id=result.inserted_id,
        buyer_id=ObjectId(current_user["id"]),
        seller_id=note["uploader_id"],
        note_id=ObjectId(note_id),
        amount=final_price,
        currency="INR",
        entry_type="purchase_success",
        source="payments.mock_checkout",
        metadata={"mock_payment_id": mock_payment_id, "mock_order_id": mock_order_id},
    )

    response = {
        "message": "Mock payment successful ✅",
        "mock": True,
        "amount_paid": final_price,
        "original_price": price,
        "discount_applied": discount_amount,
        "mock_payment_id": mock_payment_id,
    }
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
    currency = str(payment_entity.get("currency", "INR")).upper()

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
    if _is_pending_expired(purchase, int(time.time())):
        purchases_collection.update_one(
            {"_id": purchase["_id"]},
            {"$set": {"status": "expired", "expired_at": int(time.time())}},
        )
        _log_payment_event("webhook_expired_order", {"event_id": event_id, "order_id": order_id})
        return {"message": "Order expired", "processed": False}
    expected_amount = int(purchase.get("amount", 0))
    if amount is not None and expected_amount != int(amount):
        _log_payment_event(
            "webhook_amount_mismatch",
            {"event_id": event_id, "order_id": order_id, "expected": expected_amount, "received": amount},
        )
        return {"message": "Webhook amount mismatch", "processed": False}
    if currency != "INR":
        _log_payment_event(
            "webhook_currency_mismatch",
            {"event_id": event_id, "order_id": order_id, "currency": currency},
        )
        return {"message": "Webhook currency mismatch", "processed": False}

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
    _consume_coupon_usage_for_purchase(purchase)
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
