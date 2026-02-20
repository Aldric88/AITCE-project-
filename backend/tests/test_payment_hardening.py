import hashlib
import hmac
import json
from types import SimpleNamespace

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.utils.dependencies import get_current_user
from app.routes import payment_routes


class InMemoryCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    def find_one(self, query, sort=None):
        matches = [doc for doc in self.docs if self._matches(doc, query)]
        if sort and matches:
            key, direction = sort[0]
            reverse = direction == -1
            matches = sorted(matches, key=lambda d: d.get(key, 0), reverse=reverse)
        return matches[0] if matches else None

    def insert_one(self, doc):
        data = dict(doc)
        data.setdefault("_id", ObjectId())
        self.docs.append(data)
        return SimpleNamespace(inserted_id=data["_id"])

    def update_one(self, query, update, upsert=False):
        target = self.find_one(query)
        if not target:
            if upsert:
                data = dict(query)
                if "$setOnInsert" in update:
                    data.update(update["$setOnInsert"])
                if "$set" in update:
                    data.update(update["$set"])
                self.insert_one(data)
                return SimpleNamespace(modified_count=1)
            return SimpleNamespace(modified_count=0)
        if "$set" in update:
            target.update(update["$set"])
        if "$setOnInsert" in update:
            for k, v in update["$setOnInsert"].items():
                target.setdefault(k, v)
        return SimpleNamespace(modified_count=1)

    @staticmethod
    def _matches(doc, query):
        for k, v in query.items():
            if isinstance(v, dict) and "$or" in v:
                # not needed for these tests
                return False
            if doc.get(k) != v:
                return False
        return True


def _mock_user():
    return {
        "id": "507f1f77bcf86cd799439012",
        "email": "buyer@example.com",
        "name": "Buyer",
        "role": "student",
    }


def test_verify_payment_idempotent_and_replay_guard(monkeypatch):
    note_id = str(ObjectId())
    buyer_id = ObjectId(_mock_user()["id"])
    order_id = "order_test_123"

    purchases = InMemoryCollection(
        [
            {
                "_id": ObjectId(),
                "note_id": ObjectId(note_id),
                "buyer_id": buyer_id,
                "status": "pending",
                "razorpay_order_id": order_id,
                "amount": 10,
            }
        ]
    )
    monkeypatch.setattr(payment_routes, "purchases_collection", purchases)
    monkeypatch.setattr(payment_routes, "payment_events_collection", InMemoryCollection())
    monkeypatch.setattr(payment_routes, "notes_collection", InMemoryCollection())
    monkeypatch.setattr("app.services.ledger_service.ledger_entries_collection", InMemoryCollection())
    idem = InMemoryCollection()
    monkeypatch.setattr("app.utils.idempotency.idempotency_keys_collection", idem)
    monkeypatch.setattr(
        payment_routes,
        "client",
        SimpleNamespace(utility=SimpleNamespace(verify_payment_signature=lambda _: True)),
    )

    app.dependency_overrides[get_current_user] = _mock_user
    client = TestClient(app)

    payload = {
        "note_id": note_id,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": "pay_ok_1",
        "razorpay_signature": "sig_ok",
    }
    first = client.post(
        "/payments/verify",
        json=payload,
        headers={"X-Idempotency-Key": "idem-verify-1"},
    )
    assert first.status_code == 200

    second = client.post(
        "/payments/verify",
        json=payload,
        headers={"X-Idempotency-Key": "idem-verify-1"},
    )
    assert second.status_code == 200
    assert second.json().get("message") in {
        "Payment verified ✅ Purchase successful",
        "Payment already verified ✅",
    }

    replay = dict(payload)
    replay["razorpay_payment_id"] = "pay_other"
    third = client.post(
        "/payments/verify",
        json=replay,
        headers={"X-Idempotency-Key": "idem-verify-2"},
    )
    assert third.status_code == 409

    app.dependency_overrides.clear()


def test_webhook_replay_is_ignored(monkeypatch):
    note_id = ObjectId()
    order_id = "order_webhook_1"
    purchases = InMemoryCollection(
        [
            {
                "_id": ObjectId(),
                "note_id": note_id,
                "buyer_id": ObjectId(),
                "status": "pending",
                "razorpay_order_id": order_id,
                "amount": 25,
            }
        ]
    )
    webhook_events = InMemoryCollection()
    payment_events = InMemoryCollection()

    monkeypatch.setattr(payment_routes, "purchases_collection", purchases)
    monkeypatch.setattr(payment_routes, "payment_webhook_events_collection", webhook_events)
    monkeypatch.setattr(payment_routes, "payment_events_collection", payment_events)
    monkeypatch.setattr(payment_routes, "notes_collection", InMemoryCollection())
    monkeypatch.setattr("app.services.ledger_service.ledger_entries_collection", InMemoryCollection())
    idem = InMemoryCollection()
    monkeypatch.setattr("app.utils.idempotency.idempotency_keys_collection", idem)
    monkeypatch.setattr(payment_routes.settings, "RAZORPAY_WEBHOOK_SECRET", "whsec_test")

    payload = {
        "id": "evt_100",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_100",
                    "order_id": order_id,
                    "amount": 2500,
                }
            }
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    signature = hmac.new(b"whsec_test", raw, hashlib.sha256).hexdigest()

    client = TestClient(app)
    first = client.post(
        "/payments/webhook",
        data=raw,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert first.status_code == 200
    assert first.json().get("processed") is True

    second = client.post(
        "/payments/webhook",
        data=raw,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert second.status_code == 200
    assert second.json().get("idempotent") is True
