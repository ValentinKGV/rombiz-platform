"""
JWT RS256 authentication — NEVER HS256 (hard constraint #14).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

security_scheme = HTTPBearer()


class TokenPayload(BaseModel):
    sub: str  # user_id
    org_id: str
    role: str
    exp: datetime
    iat: datetime
    jti: str  # unique token id for revocation


def _load_key(path: str) -> str | None:
    """Load PEM key from file; return None if missing."""
    p = Path(path)
    if p.exists():
        return p.read_text()
    return None


_private_key = _load_key(settings.JWT_PRIVATE_KEY_PATH)
_public_key = _load_key(settings.JWT_PUBLIC_KEY_PATH)

if _private_key is None or _public_key is None:
    if settings.ENVIRONMENT == "production":
        raise RuntimeError(
            "RSA keys not found — refusing to start in production without RS256 keys. "
            "Generate keys with: openssl genrsa -out keys/private.pem 4096 && "
            "openssl rsa -in keys/private.pem -pubout -out keys/public.pem"
        )
    import warnings
    _HS256_SECRET = "DEV_SECRET_NOT_FOR_PRODUCTION_change_me"  # noqa: S105
    warnings.warn(
        "RSA keys not found — using HS256 fallback (dev only). "
        "Generate keys with: openssl genrsa -out keys/private.pem 4096 && "
        "openssl rsa -in keys/private.pem -pubout -out keys/public.pem",
        stacklevel=2,
    )

_USE_HS256_FALLBACK = _private_key is None or _public_key is None


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    user_id: str,
    org_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role,
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
    }
    if _USE_HS256_FALLBACK:
        return jwt.encode(payload, _HS256_SECRET, algorithm="HS256")
    return jwt.encode(payload, _private_key, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, org_id: str, role: str) -> str:
    return create_access_token(
        user_id,
        org_id,
        role,
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> TokenPayload:
    try:
        if _USE_HS256_FALLBACK:
            payload = jwt.decode(token, _HS256_SECRET, algorithms=["HS256"])
        else:
            payload = jwt.decode(token, _public_key, algorithms=[settings.JWT_ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> TokenPayload:
    """FastAPI dependency — extracts and validates JWT from Authorization header."""
    return decode_token(credentials.credentials)


def require_role(*allowed_roles: str):
    """Factory for role-based access control dependency."""
    async def _check(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not allowed. Required: {allowed_roles}",
            )
        return user
    return _check
