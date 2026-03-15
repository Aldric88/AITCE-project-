from types import SimpleNamespace

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.routes import purchase_routes
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
            for key, value in update["$inc"].items():
                target[key] = int(target.get(key, 0)) + int(value)
        return SimpleNamespace(modified_count=1)

    @classmethod
    def _matches(cls, doc, query):
        for key, value in query.items():
            if key == "$or":
                return any(cls._matches(doc, cond) for cond in value)
            if isinstance(value, dict):
                if "$in" in value and doc.get(key) not in value["$in"]:
                    return False
                if "$gt" in value and int(doc.get(key, 0)) <= int(value["$gt"]):
                    return False
                if "$gte" in value and int(doc.get(key, 0)) < int(value["$gte"]):
                    return False
                if "$lt" in value and int(doc.get(key, 0)) >= int(value["$lt"]):
                    return False
                continue
            if doc.get(key) != value:
                return False
        return True


def _mock_user():
    return {
        "id": "507f1f77bcf86cd799439012",
        "email": "buyer@example.com",
        "name": "Buyer",
        "role": "student",
    }


def test_paid_note_rejects_free_unlock(monkeypatch):
    # Paid notes cannot be unlocked without points — free method should return 400
    note_id = ObjectId()
    seller_id = ObjectId()

    notes = InMemoryCollection(
        [
            {
                "_id": note_id,
                "status": "approved",
                "is_paid": True,
                "price": 40,
                "uploader_id": seller_id,
            }
        ]
    )
    purchases = InMemoryCollection()
    idempotency = InMemoryCollection()
    ledger = InMemoryCollection()

    monkeypatch.setattr(purchase_routes, "notes_collection", notes)
    monkeypatch.setattr(purchase_routes, "purchases_collection", purchases)
    monkeypatch.setattr("app.utils.idempotency.idempotency_keys_collection", idempotency)
    monkeypatch.setattr("app.services.ledger_service.ledger_entries_collection", ledger)

    app.dependency_overrides[get_current_user] = _mock_user
    client = TestClient(app)

    response = client.post(
        f"/purchase/{note_id}",
        headers={"X-Idempotency-Key": "free-unlock-1"},
    )

    assert response.status_code == 400
    assert "paid note" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_already_purchased_note_returns_unlocked(monkeypatch):
    note_id = ObjectId()
    buyer_id = ObjectId(_mock_user()["id"])
    seller_id = ObjectId()

    notes = InMemoryCollection(
        [
            {
                "_id": note_id,
                "status": "approved",
                "is_paid": True,
                "price": 50,
                "uploader_id": seller_id,
            }
        ]
    )
    purchases = InMemoryCollection(
        [
            {
                "_id": ObjectId(),
                "buyer_id": buyer_id,
                "user_id": buyer_id,
                "note_id": note_id,
                "status": "success",
            }
        ]
    )
    idempotency = InMemoryCollection()
    ledger = InMemoryCollection()

    monkeypatch.setattr(purchase_routes, "notes_collection", notes)
    monkeypatch.setattr(purchase_routes, "purchases_collection", purchases)
    monkeypatch.setattr("app.utils.idempotency.idempotency_keys_collection", idempotency)
    monkeypatch.setattr("app.services.ledger_service.ledger_entries_collection", ledger)

    app.dependency_overrides[get_current_user] = _mock_user
    client = TestClient(app)

    response = client.post(
        f"/purchase/{note_id}",
        headers={"X-Idempotency-Key": "free-unlock-2"},
    )
    assert response.status_code == 200
    assert "Already unlocked" in response.json()["message"]

    app.dependency_overrides.clear()
