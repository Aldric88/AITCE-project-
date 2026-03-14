from types import SimpleNamespace

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.routes import payment_routes, dispute_routes, monetization_routes
from app.services import points_service
from app.utils.dependencies import get_current_user


class InMemoryCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    def find_one(self, query, sort=None):
        matches = [doc for doc in self.docs if self._matches(doc, query)]
        if isinstance(sort, list) and sort and matches:
            key, direction = sort[0]
            reverse = direction == -1
            matches = sorted(matches, key=lambda d: d.get(key, 0), reverse=reverse)
        return matches[0] if matches else None

    def find(self, query=None, projection=None):
        query = query or {}
        rows = [doc for doc in self.docs if self._matches(doc, query)]
        return InMemoryCursor(rows)

    def insert_one(self, doc):
        data = dict(doc)
        data.setdefault("_id", ObjectId())
        self.docs.append(data)
        return SimpleNamespace(inserted_id=data["_id"])

    def update_one(self, query, update, upsert=False):
        target = self.find_one(query)
        if not target:
            if upsert:
                doc = dict(query)
                if "$setOnInsert" in update:
                    doc.update(update["$setOnInsert"])
                if "$set" in update:
                    doc.update(update["$set"])
                self.insert_one(doc)
                return SimpleNamespace(modified_count=1)
            return SimpleNamespace(modified_count=0)
        if "$set" in update:
            target.update(update["$set"])
        if "$inc" in update:
            for k, v in update["$inc"].items():
                target[k] = int(target.get(k, 0)) + int(v)
        if "$addToSet" in update:
            for k, v in update["$addToSet"].items():
                values = target.get(k, [])
                if v not in values:
                    values.append(v)
                target[k] = values
        if "$pull" in update:
            for k, v in update["$pull"].items():
                target[k] = [item for item in target.get(k, []) if item != v]
        if "$setOnInsert" in update:
            for k, v in update["$setOnInsert"].items():
                target.setdefault(k, v)
        return SimpleNamespace(modified_count=1)

    def update_many(self, query, update):
        count = 0
        for doc in self.docs:
            if not self._matches(doc, query):
                continue
            if "$set" in update:
                doc.update(update["$set"])
            count += 1
        return SimpleNamespace(modified_count=count)

    def count_documents(self, query):
        return len([doc for doc in self.docs if self._matches(doc, query)])

    @classmethod
    def _matches(cls, doc, query):
        for key, value in query.items():
            if key == "$or":
                if not any(cls._matches(doc, branch) for branch in value):
                    return False
                continue
            if isinstance(value, dict):
                if "$in" in value and doc.get(key) not in value["$in"]:
                    return False
                if "$ne" in value and doc.get(key) == value["$ne"]:
                    return False
                if "$gt" in value and int(doc.get(key, 0)) <= int(value["$gt"]):
                    return False
                if "$gte" in value and int(doc.get(key, 0)) < int(value["$gte"]):
                    return False
                if "$lt" in value and int(doc.get(key, 0)) >= int(value["$lt"]):
                    return False
                if "$lte" in value and int(doc.get(key, 0)) > int(value["$lte"]):
                    return False
                if "$exists" in value:
                    exists = key in doc
                    if bool(value["$exists"]) != exists:
                        return False
                continue
            if doc.get(key) != value:
                return False
        return True


class InMemoryCursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, key, direction):
        reverse = direction == -1
        self.rows = sorted(self.rows, key=lambda d: d.get(key, 0), reverse=reverse)
        return self

    def limit(self, limit):
        self.rows = self.rows[:limit]
        return self

    def __iter__(self):
        return iter(self.rows)


def _buyer_user():
    return {
        "id": "507f1f77bcf86cd799439012",
        "email": "buyer@example.com",
        "name": "Buyer",
        "role": "student",
    }


def test_coupon_consumed_only_after_verify(monkeypatch):
    note_id = ObjectId()
    seller_id = ObjectId()
    coupon_code = "SAVE20"

    notes = InMemoryCollection(
        [
            {
                "_id": note_id,
                "title": "Paid Note",
                "status": "approved",
                "is_paid": True,
                "price": 100,
                "uploader_id": seller_id,
            }
        ]
    )
    purchases = InMemoryCollection()
    coupons = InMemoryCollection(
        [
            {
                "_id": ObjectId(),
                "code": coupon_code,
                "is_active": True,
                "uses": 0,
                "max_uses": 10,
                "percent_off": 20,
            }
        ]
    )
    idempotency = InMemoryCollection()

    monkeypatch.setattr(payment_routes, "notes_collection", notes)
    monkeypatch.setattr(payment_routes, "purchases_collection", purchases)
    monkeypatch.setattr(payment_routes, "coupons_collection", coupons)
    monkeypatch.setattr(payment_routes, "campaigns_collection", InMemoryCollection())
    monkeypatch.setattr(payment_routes, "payment_events_collection", InMemoryCollection())
    monkeypatch.setattr(payment_routes, "payment_webhook_events_collection", InMemoryCollection())
    monkeypatch.setattr("app.services.ledger_service.ledger_entries_collection", InMemoryCollection())
    monkeypatch.setattr("app.utils.idempotency.idempotency_keys_collection", idempotency)
    monkeypatch.setattr(
        payment_routes,
        "client",
        SimpleNamespace(
            order=SimpleNamespace(create=lambda _: {"id": "order_coupon_1"}),
            utility=SimpleNamespace(verify_payment_signature=lambda _: True),
            payment=SimpleNamespace(fetch=lambda _: {"order_id": "order_coupon_1", "amount": 8000, "currency": "INR"}),
        ),
    )

    app.dependency_overrides[get_current_user] = _buyer_user
    client = TestClient(app)

    order = client.post(
        "/payments/create-order",
        json={"note_id": str(note_id), "coupon_code": coupon_code},
        headers={"X-Idempotency-Key": "coupon-create-1"},
    )
    assert order.status_code == 200
    assert coupons.find_one({"code": coupon_code})["uses"] == 0

    verify = client.post(
        "/payments/verify",
        json={
            "note_id": str(note_id),
            "razorpay_order_id": "order_coupon_1",
            "razorpay_payment_id": "pay_coupon_1",
            "razorpay_signature": "sig_coupon_1",
        },
        headers={"X-Idempotency-Key": "coupon-verify-1"},
    )
    assert verify.status_code == 200
    assert coupons.find_one({"code": coupon_code})["uses"] == 1

    app.dependency_overrides.clear()


def test_dispute_approve_refunds_points_and_adds_negative_ledger(monkeypatch):
    dispute_id = ObjectId()
    note_id = ObjectId()
    buyer_id = ObjectId(_buyer_user()["id"])
    seller_id = ObjectId()

    disputes = InMemoryCollection(
        [
            {
                "_id": dispute_id,
                "note_id": note_id,
                "buyer_id": buyer_id,
                "status": "pending",
                "message": "refund pls",
                "created_at": 1,
            }
        ]
    )
    purchases = InMemoryCollection(
        [
            {
                "_id": ObjectId(),
                "note_id": note_id,
                "buyer_id": buyer_id,
                "status": "success",
                "purchase_type": "points",
                "currency": "POINTS",
                "amount": 40,
                "created_at": 2,
            }
        ]
    )
    notes = InMemoryCollection(
        [
            {
                "_id": note_id,
                "uploader_id": seller_id,
            }
        ]
    )
    users = InMemoryCollection(
        [
            {"_id": buyer_id, "wallet_points": 10},
            {"_id": seller_id, "wallet_points": 100},
        ]
    )
    leaderboard = InMemoryCollection()
    ledger = InMemoryCollection()

    monkeypatch.setattr(dispute_routes, "disputes_collection", disputes)
    monkeypatch.setattr(dispute_routes, "purchases_collection", purchases)
    monkeypatch.setattr(dispute_routes, "notes_collection", notes)
    monkeypatch.setattr("app.services.ledger_service.ledger_entries_collection", ledger)
    monkeypatch.setattr(points_service, "users_collection", users)
    monkeypatch.setattr(points_service, "leaderboard_collection", leaderboard)

    result = dispute_routes.approve_dispute(
        dispute_id=str(dispute_id),
        current_user={"id": "admin1", "role": "admin", "email": "admin@example.com"},
    )

    assert result["refund_status"] == "refund_success"
    assert purchases.find_one({"note_id": note_id})["status"] == "refunded"
    assert users.find_one({"_id": buyer_id})["wallet_points"] == 50
    assert users.find_one({"_id": seller_id})["wallet_points"] == 60
    assert any(int(entry.get("amount", 0)) < 0 for entry in ledger.docs)


def test_creator_pass_subscription_requires_points_and_activates(monkeypatch):
    pass_id = ObjectId()
    seller_id = ObjectId()
    buyer_id = ObjectId(_buyer_user()["id"])
    now_ts = 1_700_000_000

    passes = InMemoryCollection(
        [
            {
                "_id": pass_id,
                "seller_id": seller_id,
                "is_active": True,
                "monthly_price": 30,
                "duration_days": 30,
                "max_subscribers": None,
            }
        ]
    )
    subs = InMemoryCollection()
    users = InMemoryCollection(
        [
            {"_id": buyer_id, "wallet_points": 100},
            {"_id": seller_id, "wallet_points": 0},
        ]
    )
    leaderboard = InMemoryCollection()
    ledger = InMemoryCollection()

    monkeypatch.setattr(monetization_routes, "creator_passes_collection", passes)
    monkeypatch.setattr(monetization_routes, "pass_subscriptions_collection", subs)
    monkeypatch.setattr(monetization_routes, "ledger_entries_collection", ledger)
    monkeypatch.setattr(points_service, "users_collection", users)
    monkeypatch.setattr(points_service, "leaderboard_collection", leaderboard)
    monkeypatch.setattr(monetization_routes.time, "time", lambda: now_ts)

    response = monetization_routes.subscribe_creator_pass(
        pass_id=str(pass_id),
        data=monetization_routes.SubscribePassRequest(payment_method="points"),
        current_user={"id": str(buyer_id), "role": "student"},
    )
    assert response["message"].startswith("Creator pass subscription active")
    assert response["wallet_points"] == 70
    assert subs.count_documents({"pass_id": pass_id, "status": "active"}) == 1
    assert users.find_one({"_id": seller_id})["wallet_points"] == 24
