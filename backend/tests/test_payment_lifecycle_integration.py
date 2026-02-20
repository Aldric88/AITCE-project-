from types import SimpleNamespace

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.routes import payment_routes
from app.utils.dependencies import get_current_user


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
        if target:
            if "$set" in update:
                target.update(update["$set"])
            if "$setOnInsert" in update:
                for k, v in update["$setOnInsert"].items():
                    target.setdefault(k, v)
            return SimpleNamespace(modified_count=1)
        if upsert:
            data = dict(query)
            if "$set" in update:
                data.update(update["$set"])
            if "$setOnInsert" in update:
                data.update(update["$setOnInsert"])
            self.insert_one(data)
            return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)

    @staticmethod
    def _matches(doc, query):
        for key, val in query.items():
            if isinstance(val, dict):
                return False
            if doc.get(key) != val:
                return False
        return True


def test_paid_purchase_lifecycle_create_then_verify(monkeypatch):
    note_id = ObjectId()
    buyer_id = "507f1f77bcf86cd799439012"
    seller_id = ObjectId()

    notes = InMemoryCollection(
        [
            {
                "_id": note_id,
                "title": "Paid Note",
                "status": "approved",
                "is_paid": True,
                "price": 25,
                "uploader_id": seller_id,
            }
        ]
    )
    purchases = InMemoryCollection()
    idempotency = InMemoryCollection()
    events = InMemoryCollection()
    ledger = InMemoryCollection()

    monkeypatch.setattr(payment_routes, "notes_collection", notes)
    monkeypatch.setattr(payment_routes, "purchases_collection", purchases)
    monkeypatch.setattr(payment_routes, "payment_events_collection", events)
    monkeypatch.setattr(payment_routes, "payment_webhook_events_collection", InMemoryCollection())
    monkeypatch.setattr(payment_routes, "idempotency_keys_collection", idempotency, raising=False)
    monkeypatch.setattr("app.utils.idempotency.idempotency_keys_collection", idempotency)
    monkeypatch.setattr("app.services.ledger_service.ledger_entries_collection", ledger)
    monkeypatch.setattr(
        payment_routes,
        "client",
        SimpleNamespace(
            order=SimpleNamespace(create=lambda _: {"id": "order_int_1"}),
            utility=SimpleNamespace(verify_payment_signature=lambda _: True),
        ),
    )

    app.dependency_overrides[get_current_user] = lambda: {
        "id": buyer_id,
        "email": "buyer@example.com",
        "name": "Buyer",
        "role": "student",
    }
    client = TestClient(app)

    order = client.post(
        "/payments/create-order",
        json={"note_id": str(note_id)},
        headers={"X-Idempotency-Key": "create-1"},
    )
    assert order.status_code == 200
    assert order.json()["order_id"] == "order_int_1"
    assert purchases.find_one({"razorpay_order_id": "order_int_1"}) is not None

    verify = client.post(
        "/payments/verify",
        json={
            "note_id": str(note_id),
            "razorpay_order_id": "order_int_1",
            "razorpay_payment_id": "pay_int_1",
            "razorpay_signature": "sig_int_1",
        },
        headers={"X-Idempotency-Key": "verify-1"},
    )
    assert verify.status_code == 200

    purchase = purchases.find_one({"razorpay_order_id": "order_int_1"})
    assert purchase is not None
    assert purchase["status"] == "success"
    assert purchase["razorpay_payment_id"] == "pay_int_1"
    assert len(ledger.docs) == 1

    app.dependency_overrides.clear()
