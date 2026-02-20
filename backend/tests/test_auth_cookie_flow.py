from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.routes import auth_routes


class InMemoryCollection:
    def __init__(self):
        self.docs = []

    def insert_one(self, doc):
        self.docs.append(dict(doc))

    def update_one(self, query, update, upsert=False):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                if "$set" in update:
                    doc.update(update["$set"])
                return
        if upsert:
            data = dict(query)
            if "$setOnInsert" in update:
                data.update(update["$setOnInsert"])
            if "$set" in update:
                data.update(update["$set"])
            self.docs.append(data)

    def find_one(self, query):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None


def test_login_sets_http_only_cookie(monkeypatch):
    def fake_authenticate_user(email, password):
        return {
            "id": "507f1f77bcf86cd799439011",
            "name": "Test",
            "email": email,
            "role": "student",
            "dept": "CSE",
            "year": 3,
            "section": "A",
        }

    monkeypatch.setattr(auth_routes, "authenticate_user", fake_authenticate_user)
    monkeypatch.setattr(auth_routes, "refresh_tokens_collection", InMemoryCollection())
    monkeypatch.setattr(auth_routes, "revoked_tokens_collection", InMemoryCollection())

    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            data={"username": "user@example.com", "password": "pass1234"},
        )

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert settings.JWT_COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie


def test_logout_clears_cookie(monkeypatch):
    monkeypatch.setattr(auth_routes, "refresh_tokens_collection", InMemoryCollection())
    monkeypatch.setattr(auth_routes, "revoked_tokens_collection", InMemoryCollection())
    with TestClient(app) as client:
        response = client.post("/auth/logout")

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert settings.JWT_COOKIE_NAME in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()
