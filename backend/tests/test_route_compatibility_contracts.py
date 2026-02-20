from types import SimpleNamespace

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.routes import note_routes, purchase_routes
from app.utils.dependencies import get_current_user


class InMemoryCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, key, direction):
        reverse = direction == -1
        self.docs.sort(key=lambda d: d.get(key), reverse=reverse)
        return self

    def __iter__(self):
        return iter(self.docs)


class InMemoryCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def find_one(self, query, sort=None):
        matches = [doc for doc in self.docs if self._matches(doc, query)]
        if sort and matches:
            key, direction = sort[0]
            reverse = direction == -1
            matches = sorted(matches, key=lambda d: d.get(key), reverse=reverse)
        return matches[0] if matches else None

    def find(self, query=None, projection=None):
        query = query or {}
        matches = [doc for doc in self.docs if self._matches(doc, query)]
        if projection:
            projected = []
            include_keys = {k for k, v in projection.items() if v}
            for doc in matches:
                out = {"_id": doc.get("_id")}
                for key in include_keys:
                    if key in doc:
                        out[key] = doc[key]
                projected.append(out)
            return InMemoryCursor(projected)
        return InMemoryCursor(matches)

    def insert_one(self, doc):
        data = dict(doc)
        data.setdefault("_id", ObjectId())
        self.docs.append(data)
        return SimpleNamespace(inserted_id=data["_id"])

    @classmethod
    def _matches(cls, doc, query):
        for key, val in query.items():
            if key == "$or":
                if not any(cls._matches(doc, part) for part in val):
                    return False
                continue
            if isinstance(val, dict) and "$in" in val:
                if doc.get(key) not in val["$in"]:
                    return False
                continue
            if isinstance(val, dict) and "$exists" in val:
                exists = key in doc
                if exists != bool(val["$exists"]):
                    return False
                continue
            if doc.get(key) != val:
                return False
        return True


def _mock_user():
    return {
        "id": "507f1f77bcf86cd799439012",
        "email": "buyer@example.com",
        "name": "Buyer",
        "role": "student",
    }


def test_purchase_aliases_and_response_shape(monkeypatch):
    note_id = ObjectId("507f1f77bcf86cd799439020")
    uploader_id = ObjectId("507f1f77bcf86cd799439099")

    notes = InMemoryCollection(
        [
            {
                "_id": note_id,
                "title": "Signals Unit 1",
                "subject": "Signals",
                "unit": 1,
                "semester": 4,
                "dept": "ECE",
                "description": "short notes",
                "status": "approved",
                "is_paid": False,
                "price": 0,
                "uploader_id": uploader_id,
            }
        ]
    )
    purchases = InMemoryCollection()
    ledger_calls = []

    monkeypatch.setattr(purchase_routes, "notes_collection", notes)
    monkeypatch.setattr(purchase_routes, "purchases_collection", purchases)
    monkeypatch.setattr(purchase_routes, "add_ledger_entry", lambda **kwargs: ledger_calls.append(kwargs))
    monkeypatch.setattr(purchase_routes, "make_request_fingerprint", lambda payload: "fp-1")
    monkeypatch.setattr(purchase_routes, "get_saved_idempotent_response", lambda *args, **kwargs: None)
    monkeypatch.setattr(purchase_routes, "save_idempotent_response", lambda *args, **kwargs: None)

    app.dependency_overrides[get_current_user] = _mock_user
    client = TestClient(app)

    buy = client.post(f"/purchases/{note_id}", headers={"X-Idempotency-Key": "idem-buy-1"})
    assert buy.status_code == 200
    assert buy.json()["paid"] is False
    assert len(ledger_calls) == 1

    mine_canonical = client.get("/purchase/my")
    mine_plural = client.get("/purchases/my")
    assert mine_canonical.status_code == 200
    assert mine_plural.status_code == 200
    assert mine_canonical.json() == mine_plural.json()

    body = mine_canonical.json()
    assert len(body) == 1
    row = body[0]
    assert row["purchase_id"]
    assert row["note_id"] == str(note_id)
    assert row["unlocked_type"] == "free"
    assert row["note"]["title"] == "Signals Unit 1"
    assert row["note"]["subject"] == "Signals"

    has_canonical = client.get(f"/purchase/has/{note_id}")
    has_plural = client.get(f"/purchases/has/{note_id}")
    assert has_canonical.status_code == 200
    assert has_plural.status_code == 200
    assert has_canonical.json() == {"has_access": True}
    assert has_plural.json() == {"has_access": True}

    library = client.get("/library/my")
    assert library.status_code == 200
    library_rows = library.json()
    assert len(library_rows) == 1
    assert library_rows[0]["purchase_id"] == row["purchase_id"]
    assert library_rows[0]["title"] == "Signals Unit 1"
    assert library_rows[0]["is_paid"] is False

    app.dependency_overrides.clear()


def test_notes_my_uploads_alias_matches_my(monkeypatch):
    owner_id = ObjectId("507f1f77bcf86cd799439012")
    other_id = ObjectId("507f1f77bcf86cd799439013")
    older_id = ObjectId("507f1f77bcf86cd799439101")
    newer_id = ObjectId("507f1f77bcf86cd799439102")

    notes = InMemoryCollection(
        [
            {
                "_id": older_id,
                "title": "Older Owner Note",
                "dept": "CSE",
                "semester": 3,
                "subject": "DBMS",
                "note_type": "pdf",
                "uploader_id": owner_id,
            },
            {
                "_id": newer_id,
                "title": "Newer Owner Note",
                "dept": "CSE",
                "semester": 4,
                "subject": "OS",
                "note_type": "pdf",
                "uploader_id": owner_id,
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439103"),
                "title": "Other User Note",
                "dept": "CSE",
                "semester": 2,
                "subject": "Math",
                "note_type": "pdf",
                "uploader_id": other_id,
            },
        ]
    )

    monkeypatch.setattr(note_routes, "notes_collection", notes)
    app.dependency_overrides[get_current_user] = _mock_user
    client = TestClient(app)

    mine = client.get("/notes/my")
    mine_alias = client.get("/notes/my-uploads")
    assert mine.status_code == 200
    assert mine_alias.status_code == 200
    assert mine.json() == mine_alias.json()
    assert len(mine.json()) == 2
    assert mine.json()[0]["title"] == "Newer Owner Note"
    assert mine.json()[1]["title"] == "Older Owner Note"

    app.dependency_overrides.clear()
