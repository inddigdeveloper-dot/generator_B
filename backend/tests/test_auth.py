import pytest
from app.services.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


# ── password hashing ──────────────────────────────────────────────────────────

def test_password_hash_and_verify():
    hashed = get_password_hash("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_different_passwords_produce_different_hashes():
    assert get_password_hash("abc") != get_password_hash("abc")  # argon2 is salted


# ── access tokens ─────────────────────────────────────────────────────────────

def test_create_and_decode_access_token():
    token = create_access_token({"sub": "testuser"})
    payload = decode_token(token)
    assert payload["sub"] == "testuser"
    assert payload["type"] == "access"


def test_access_token_rejects_refresh_token():
    from fastapi import HTTPException
    refresh = create_refresh_token({"sub": "testuser"})
    payload = decode_token(refresh)
    assert payload["type"] == "refresh"


# ── refresh tokens ────────────────────────────────────────────────────────────

def test_create_and_decode_refresh_token():
    token = create_refresh_token({"sub": "testuser"})
    payload = decode_token(token)
    assert payload["sub"] == "testuser"
    assert payload["type"] == "refresh"


# ── register / login endpoints ────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "name": "Test User",
    "user_name": "testuser",
    "business_name": "Test Biz",
    "email": "test@example.com",
    "seo_keyword": ["seo", "local"],
    "mobile_no": "9999999999",
    "password": "StrongPass1!",
    "review_link": "https://g.page/test",
    "business_desc": "A test business.",
}


def test_register_success(client):
    resp = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["business_name"] == "Test Biz"


def test_register_duplicate_username(client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    resp = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 400


def test_login_success(client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    resp = client.post(
        "/auth/login",
        json={"login_id": "test@example.com", "password": "StrongPass1!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    resp = client.post(
        "/auth/login",
        json={"login_id": "testuser", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_me_endpoint(client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    login = client.post(
        "/auth/login",
        json={"login_id": "testuser", "password": "StrongPass1!"},
    )
    token = login.json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["user_name"] == "testuser"


def test_refresh_endpoint(client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    login = client.post(
        "/auth/login",
        json={"login_id": "testuser", "password": "StrongPass1!"},
    )
    refresh_token = login.json()["refresh_token"]
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
