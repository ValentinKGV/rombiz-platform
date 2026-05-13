"""
Admin dashboard endpoints — system health, data source monitoring, user management.

Branch 11 improvements:
  11.1: User management (invite, role change, deactivate)
  11.2: Organization management (plan update)
  11.3: Data source monitoring (enhanced)
  11.4: GDPR audit endpoints
  11.5: System config (feature flags)
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    get_current_user, require_role, TokenPayload, hash_password,
)
from app.models.models import (
    User, Organization, Company, DataSourceSyncLog,
    AuditLog, Alert, ReportExport, BlockchainBlock, CustodyRecord, DocumentHash,
)
from app.schemas.schemas import AdminDashboardSchema, DataSourceHealthSchema

router = APIRouter()


# ──────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=AdminDashboardSchema)
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """Admin dashboard with system overview."""
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)

    total_companies, total_users, total_orgs, alerts_today, calls_today = await asyncio.gather(
        db.execute(select(func.count(Company.id))),
        db.execute(select(func.count(User.id))),
        db.execute(select(func.count(Organization.id))),
        db.execute(
            select(func.count(Alert.id)).where(Alert.created_at >= today_start)
        ),
        db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.created_at >= today_start)
        ),
    )

    return AdminDashboardSchema(
        total_companies=total_companies.scalar() or 0,
        total_users=total_users.scalar() or 0,
        total_organizations=total_orgs.scalar() or 0,
        total_alerts_today=alerts_today.scalar() or 0,
        api_calls_today=calls_today.scalar() or 0,
    )


# ──────────────────────────────────────────────────────────────────
# 11.3: Data Source Monitoring (enhanced)
# ──────────────────────────────────────────────────────────────────

@router.get("/data-sources", response_model=list[DataSourceHealthSchema])
async def data_sources_health(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """Health status of all data source connectors."""
    subquery = (
        select(
            DataSourceSyncLog.source_name,
            func.max(DataSourceSyncLog.started_at).label("last_sync"),
        )
        .group_by(DataSourceSyncLog.source_name)
        .subquery()
    )

    result = await db.execute(
        select(DataSourceSyncLog)
        .join(
            subquery,
            (DataSourceSyncLog.source_name == subquery.c.source_name) &
            (DataSourceSyncLog.started_at == subquery.c.last_sync)
        )
    )
    syncs = result.scalars().all()

    return [
        DataSourceHealthSchema(
            source_name=s.source_name,
            status=s.status,
            last_sync_at=s.started_at,
            records_processed=s.records_processed,
            records_failed=s.records_failed,
            error_message=s.error_message,
        )
        for s in syncs
    ]


@router.get("/data-sources/{source}/history")
async def data_source_history(
    source: str,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """11.3: Get sync history for a specific data source."""
    result = await db.execute(
        select(DataSourceSyncLog)
        .where(DataSourceSyncLog.source_name == source)
        .order_by(DataSourceSyncLog.started_at.desc())
        .limit(limit)
    )
    syncs = result.scalars().all()
    return [
        {
            "id": s.id,
            "source": s.source_name,
            "status": s.status,
            "started_at": s.started_at,
            "finished_at": s.completed_at,
            "records_processed": s.records_processed,
            "records_failed": s.records_failed,
            "error_message": s.error_message,
        }
        for s in syncs
    ]


# ──────────────────────────────────────────────────────────────────
# Audit Log
# ──────────────────────────────────────────────────────────────────

@router.get("/audit-log")
async def get_audit_log(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, le=200),
    action: str = None,
    user_id: str = None,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """Get audit log entries (GDPR compliance)."""
    query = select(AuditLog)

    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    offset = (page - 1) * per_page
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "user_id": str(e.user_id),
            "action": e.action,
            "entity_type": e.entity_type,
            "payload": e.payload_json,
            "ip_address": e.ip_address,
            "created_at": e.created_at,
        }
        for e in entries
    ]


# ──────────────────────────────────────────────────────────────────
# 11.1: User Management
# ──────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, le=200),
    role: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """List all users with filters."""
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) |
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%"))
        )

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(User.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    users = result.scalars().all()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "full_name": f"{u.first_name or ''} {u.last_name or ''}".strip(),
                "role": u.role,
                "is_active": u.is_active,
                "org_id": str(u.org_id) if u.org_id else None,
                "credits_left": u.credits_left,
                "created_at": u.created_at,
                "last_login": u.last_login,
            }
            for u in users
        ],
    }


class InviteUserRequest(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "viewer"
    org_id: Optional[str] = None


@router.post("/users/invite")
async def invite_user(
    body: InviteUserRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """11.1: Invite a new user. Creates account with temp password."""
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    if body.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")

    org_id = uuid.UUID(body.org_id) if body.org_id else uuid.UUID(user.org_id)

    # Create user with random temp password
    temp_password = str(uuid.uuid4())[:12]
    new_user = User(
        email=body.email,
        password_hash=hash_password(temp_password),
        first_name=body.first_name,
        last_name=body.last_name,
        role=body.role,
        org_id=org_id,
        is_active=True,
    )
    db.add(new_user)

    # Audit log
    audit = AuditLog(
        user_id=uuid.UUID(user.sub),
        action="USER_INVITED",
        entity_type="user",
        payload_json={"email": body.email, "role": body.role},
        ip_address="api",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_user)

    return {
        "user_id": str(new_user.id),
        "email": body.email,
        "temp_password": temp_password,
        "message": "User created. Share temp password securely.",
    }


class ChangeRoleRequest(BaseModel):
    role: str


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: str,
    body: ChangeRoleRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """11.1: Change a user's role."""
    if body.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = target.role
    target.role = body.role

    # Audit
    audit = AuditLog(
        user_id=uuid.UUID(user.sub),
        action="ROLE_CHANGED",
        entity_type="user",
        payload_json={"target_user": user_id, "old_role": old_role, "new_role": body.role},
        ip_address="api",
    )
    db.add(audit)
    await db.commit()

    return {"user_id": user_id, "old_role": old_role, "new_role": body.role}


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """Activate or deactivate a user."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.is_active = not target_user.is_active

    # Audit
    audit = AuditLog(
        user_id=uuid.UUID(user.sub),
        action="USER_TOGGLED",
        entity_type="user",
        payload_json={"target_user": user_id, "is_active": target_user.is_active},
        ip_address="api",
    )
    db.add(audit)
    await db.commit()
    return {"user_id": user_id, "is_active": target_user.is_active}


# ──────────────────────────────────────────────────────────────────
# 11.2: Organization Management
# ──────────────────────────────────────────────────────────────────

@router.get("/organizations")
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """List all organizations with user counts."""
    result = await db.execute(
        select(
            Organization.id,
            Organization.name,
            Organization.subscription_plan,
            Organization.subscription_status,
            Organization.api_calls_limit,
            Organization.monthly_api_calls,
            Organization.created_at,
            func.count(User.id).label("user_count"),
        )
        .outerjoin(User, User.org_id == Organization.id)
        .group_by(
            Organization.id, Organization.name, Organization.subscription_plan,
            Organization.subscription_status, Organization.api_calls_limit,
            Organization.monthly_api_calls, Organization.created_at,
        )
        .order_by(Organization.created_at.desc())
    )
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "plan": r.subscription_plan,
            "status": r.subscription_status,
            "api_calls": r.monthly_api_calls,
            "api_limit": r.api_calls_limit,
            "user_count": r.user_count,
            "created_at": r.created_at,
        }
        for r in result.all()
    ]


class UpdateOrgPlanRequest(BaseModel):
    plan: str
    api_calls_limit: Optional[int] = None


@router.put("/organizations/{org_id}/plan")
async def update_org_plan(
    org_id: str,
    body: UpdateOrgPlanRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """11.2: Update organization subscription plan."""
    valid_plans = ("FREE", "STARTER", "PROFESSIONAL", "ENTERPRISE")
    if body.plan not in valid_plans:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Valid: {valid_plans}")

    result = await db.execute(
        select(Organization).where(Organization.id == uuid.UUID(org_id))
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    old_plan = org.subscription_plan
    org.subscription_plan = body.plan
    if body.api_calls_limit is not None:
        org.api_calls_limit = body.api_calls_limit
    else:
        # Default limits per plan
        plan_limits = {"FREE": 100, "STARTER": 1000, "PROFESSIONAL": 10000, "ENTERPRISE": 100000}
        org.api_calls_limit = plan_limits.get(body.plan, 100)

    audit = AuditLog(
        user_id=uuid.UUID(user.sub),
        action="PLAN_CHANGED",
        entity_type="organization",
        payload_json={"org_id": org_id, "old_plan": old_plan, "new_plan": body.plan},
        ip_address="api",
    )
    db.add(audit)
    await db.commit()

    return {"org_id": org_id, "old_plan": old_plan, "new_plan": body.plan, "api_limit": org.api_calls_limit}


# ──────────────────────────────────────────────────────────────────
# 11.4: GDPR Endpoints
# ──────────────────────────────────────────────────────────────────

@router.post("/gdpr/export/{user_id}")
async def gdpr_export(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """11.4: Export all data for a user (GDPR Right to Data Portability)."""
    from app.middleware.gdpr import gdpr_export_user_data
    data = await gdpr_export_user_data(db, uuid.UUID(user_id))
    return data


@router.post("/gdpr/anonymize/{user_id}")
async def gdpr_anonymize(
    user_id: str,
    reason: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """11.4: Anonymize a user (GDPR Right to Erasure)."""
    from app.middleware.gdpr import gdpr_anonymize_user
    result = await gdpr_anonymize_user(db, uuid.UUID(user_id), reason)
    return result


@router.post("/gdpr/delete-company/{company_id}")
async def gdpr_delete_company(
    company_id: int,
    reason: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """11.4: Soft-delete company and cascade (GDPR)."""
    from app.middleware.gdpr import gdpr_soft_delete_company
    result = await gdpr_soft_delete_company(db, company_id, uuid.UUID(user.sub), reason)
    return result


# ──────────────────────────────────────────────────────────────────
# 11.5: System Config / Feature Flags
# ──────────────────────────────────────────────────────────────────

# Simple in-memory feature flags backed by Redis
DEFAULT_FLAGS = {
    "esg_scoring_enabled": True,
    "fraud_detection_enabled": True,
    "ai_agent_enabled": True,
    "redbill_enabled": False,
    "seap_sync_enabled": True,
    "email_notifications_enabled": True,
    "sms_notifications_enabled": False,
    "maintenance_mode": False,
}


@router.get("/config/feature-flags")
async def get_feature_flags(
    user: TokenPayload = Depends(require_role("admin")),
):
    """11.5: Get all feature flags."""
    try:
        from app.core.redis import redis_client
        import json
        raw = await redis_client.get("system:feature_flags")
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return DEFAULT_FLAGS


@router.put("/config/feature-flags")
async def set_feature_flags(
    flags: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """11.5: Update feature flags."""
    # Merge with defaults
    current = dict(DEFAULT_FLAGS)
    current.update(flags)

    try:
        from app.core.redis import redis_client
        import json
        await redis_client.set("system:feature_flags", json.dumps(current))
    except Exception:
        pass

    # Audit
    audit = AuditLog(
        user_id=uuid.UUID(user.sub),
        action="FLAGS_UPDATED",
        entity_type="system",
        payload_json=flags,
        ip_address="api",
    )
    db.add(audit)
    await db.commit()

    return current


# ──────────────────────────────────────────────────────────────────
# Sync & DB Stats
# ──────────────────────────────────────────────────────────────────

@router.post("/sync/{source}")
async def trigger_sync(
    source: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """Manually trigger a data source sync."""
    valid_sources = ["anaf", "onrc", "bpi", "portal_just", "seap", "bnr",
                     "monitor_oficial", "aegrm", "osim", "mysmis",
                     "anaf_balance", "new_companies"]
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Invalid source. Valid: {valid_sources}")

    from app.tasks.sync_tasks import trigger_source_sync
    task = trigger_source_sync.delay(source)

    # Audit
    audit = AuditLog(
        user_id=uuid.UUID(user.sub),
        action="SYNC_TRIGGERED",
        entity_type="data_source",
        payload_json={"source": source},
        ip_address="api",
    )
    db.add(audit)
    await db.commit()

    return {"status": "triggered", "source": source, "task_id": str(task.id)}


@router.get("/db-stats")
async def database_stats(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """Database statistics — table sizes, row counts."""
    try:
        result = await db.execute(text("""
            SELECT
                schemaname,
                relname as table_name,
                n_live_tup as row_count,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
        """))
        rows = result.all()
        return [
            {
                "schema": r.schemaname,
                "table": r.table_name,
                "rows": r.row_count,
                "size": r.total_size,
            }
            for r in rows
        ]
    except Exception:
        # SQLite fallback
        return [{"info": "DB stats only available with PostgreSQL"}]


# ──────────────────────────────────────────────────────────────────
# Blockchain Audit Trail Viewer
# ──────────────────────────────────────────────────────────────────

@router.get("/blockchain-trail")
async def blockchain_trail(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("admin")),
):
    """Paginated blockchain blocks + document hashes + custody records."""
    offset = (page - 1) * per_page

    # Total blocks
    total_result = await db.execute(select(func.count(BlockchainBlock.id)))
    total_blocks = total_result.scalar() or 0

    # Chain validity
    from app.services.blockchain_audit import _verify_chain
    chain_valid = await _verify_chain(db)

    # Paginated blocks (most recent first)
    blocks_result = await db.execute(
        select(BlockchainBlock)
        .order_by(BlockchainBlock.block_index.desc())
        .offset(offset)
        .limit(per_page)
    )
    blocks = blocks_result.scalars().all()

    # Stats
    doc_count_result = await db.execute(select(func.count(DocumentHash.id)))
    custody_count_result = await db.execute(select(func.count(CustodyRecord.id)))

    return {
        "blocks": [
            {
                "index": b.block_index,
                "hash": b.block_hash,
                "previous_hash": b.previous_hash,
                "data": b.data_json,
                "nonce": b.nonce,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in blocks
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_blocks,
            "pages": (total_blocks + per_page - 1) // per_page if per_page else 0,
        },
        "stats": {
            "total_blocks": total_blocks,
            "chain_valid": chain_valid,
            "total_documents": doc_count_result.scalar() or 0,
            "total_custody_records": custody_count_result.scalar() or 0,
        },
    }
