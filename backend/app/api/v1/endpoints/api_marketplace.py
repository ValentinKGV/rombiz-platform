"""
API Marketplace endpoints — key management, usage analytics,
rate limits, SDK docs, and webhook management.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.api_marketplace import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
    usage_analytics,
    get_rate_limits,
    generate_sdk_docs,
    manage_webhooks,
)

router = APIRouter()


# ── Pydantic body models ──────────────────────────────────────
class CreateKeyBody(BaseModel):
    name: str = "Default Key"
    scopes: list[str] | None = None
    expires_days: int = 365


class WebhookBody(BaseModel):
    action: str = "list"
    webhook_url: str | None = None
    events: list[str] | None = None
    webhook_id: str | None = None


# ── Endpoints ─────────────────────────────────────────────────
@router.post("/keys")
async def create_key(
    body: CreateKeyBody,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await create_api_key(db, user.sub, body.name, body.scopes, body.expires_days)


@router.get("/keys")
async def list_keys(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await list_api_keys(db, user.sub)


@router.delete("/keys/{key_id}")
async def revoke_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await revoke_api_key(db, user.sub, key_id)


@router.get("/usage")
async def get_usage(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await usage_analytics(db, user.sub, days)


@router.get("/rate-limits")
async def get_limits(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await get_rate_limits(db, user.sub)


@router.get("/sdk/{language}")
async def get_sdk(
    language: str = "python",
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await generate_sdk_docs(db, language)


@router.post("/webhooks")
async def webhooks(
    body: WebhookBody,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return await manage_webhooks(
        db, user.sub, body.action, body.webhook_url, body.events, body.webhook_id
    )
