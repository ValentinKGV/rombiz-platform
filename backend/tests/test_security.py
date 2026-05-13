"""
Unit tests for the security module: hashing, JWT tokens, role checks.
"""
from datetime import timedelta, datetime, timezone

import pytest
from fastapi import HTTPException

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    TokenPayload,
)


# ── Password hashing ──────────────────────────────────────────


def test_hash_password_returns_bcrypt():
    h = hash_password("TestPass123!")
    assert h.startswith("$2")
    assert len(h) > 50


def test_hash_password_different_each_time():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2


def test_verify_password_correct():
    h = hash_password("correct-horse")
    assert verify_password("correct-horse", h) is True


def test_verify_password_wrong():
    h = hash_password("correct-horse")
    assert verify_password("wrong-horse", h) is False


# ── JWT token creation & decoding ──────────────────────────────


def test_create_access_token_returns_str():
    token = create_access_token("user-1", "org-1", "admin")
    assert isinstance(token, str)
    assert len(token) > 20


def test_decode_access_token_payload():
    token = create_access_token("user-42", "org-7", "analyst")
    payload = decode_token(token)
    assert isinstance(payload, TokenPayload)
    assert payload.sub == "user-42"
    assert payload.org_id == "org-7"
    assert payload.role == "analyst"
    assert payload.jti  # non-empty
    assert payload.iat <= datetime.now(timezone.utc)
    assert payload.exp > datetime.now(timezone.utc)


def test_create_access_token_custom_expiry():
    token = create_access_token("u", "o", "viewer", expires_delta=timedelta(seconds=5))
    payload = decode_token(token)
    # Should expire within ~10 seconds of now (allowing clock skew)
    assert (payload.exp - payload.iat).total_seconds() <= 10


def test_create_refresh_token():
    token = create_refresh_token("u1", "o1", "admin")
    payload = decode_token(token)
    assert payload.sub == "u1"
    # Refresh tokens should live > 1 day
    diff = (payload.exp - payload.iat).total_seconds()
    assert diff > 86400


def test_decode_token_invalid_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not.a.valid.token")
    assert exc_info.value.status_code == 401


def test_decode_token_expired_raises_401():
    token = create_access_token("u", "o", "v", expires_delta=timedelta(seconds=-10))
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


def test_tokens_have_unique_jti():
    t1 = create_access_token("u", "o", "admin")
    t2 = create_access_token("u", "o", "admin")
    p1 = decode_token(t1)
    p2 = decode_token(t2)
    assert p1.jti != p2.jti
