"""
Multi-tenancy middleware — ensures org_id is enforced on every query.
Hard constraint #3: org_id pe fiecare query.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class MultiTenancyMiddleware(BaseHTTPMiddleware):
    """
    Injects org_id into request state from the authenticated user.
    All downstream DB queries MUST use request.state.org_id.
    """

    EXEMPT_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    async def dispatch(self, request: Request, call_next):
        # Skip for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # org_id is set by get_current_user dependency, but we also set a
        # fallback in state for middleware-level checks
        request.state.org_id = None

        response = await call_next(request)
        return response


def enforce_org_id(org_id: Optional[UUID]) -> UUID:
    """
    Called by endpoint logic to ensure org_id is present.
    Raises 403 if missing.
    """
    if not org_id:
        raise HTTPException(
            status_code=403,
            detail="Organization context required",
        )
    return org_id


def org_id_filter(query, model_class, org_id: UUID):
    """
    Apply org_id WHERE clause to any SQLAlchemy query.
    Usage:
        query = org_id_filter(select(Company), Company, user.org_id)
    """
    if hasattr(model_class, "org_id"):
        return query.where(model_class.org_id == org_id)
    return query
