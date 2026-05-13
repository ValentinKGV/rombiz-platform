"""
Alerts & WebSocket endpoints — 13 alert types, real-time notifications.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, TokenPayload
from app.models.models import Alert, Company, MonitoredPortfolio, PortfolioCompany, User
from app.schemas.schemas import AlertSchema

router = APIRouter()


def _to_uuid(val):
    """Convert string to UUID if needed."""
    import uuid as _uuid
    if isinstance(val, _uuid.UUID):
        return val
    return _uuid.UUID(str(val))

# ── WebSocket connection manager ──
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id] if ws != websocket
            ]

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

    async def broadcast_to_org(self, org_id: str, message: dict):
        # In production use Redis pub/sub for cross-process broadcasting
        pass


manager = ConnectionManager()


@router.websocket("/ws/{token}")
async def websocket_alerts(websocket: WebSocket, token: str):
    """
    WebSocket endpoint for real-time alerts.
    Client connects with JWT token in URL path.
    """
    from app.core.security import decode_token
    try:
        payload = decode_token(token)
        user_id = payload.sub
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive, receive client messages
            data = await websocket.receive_json()
            # Handle client messages (e.g., mark as read)
            if data.get("action") == "mark_read" and data.get("alert_id"):
                # Mark alert as read via async DB session
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@router.get("")
async def list_alerts(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, le=100),
    tip_alerta: Optional[str] = None,
    citit: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    List alerts for the current user.
    13 alert types supported:
      1. fiscal_status_change
      2. insolvency_opened
      3. new_court_case
      4. financial_data_published
      5. administrator_change
      6. associates_change
      7. new_public_contract
      8. risk_score_degraded
      9. address_change
      10. caen_change
      11. new_mo_mention
      12. debt_status_change
      13. esg_score_change
    """
    query = select(Alert).where(Alert.user_id == user.sub)

    if tip_alerta:
        query = query.where(Alert.tip_alerta == tip_alerta)
    if citit is not None:
        query = query.where(Alert.citita == citit)

    offset = (page - 1) * per_page
    query = query.order_by(Alert.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    alerts = result.scalars().all()

    # Collect company IDs to fetch company_name and company_cui
    company_ids = [a.company_id for a in alerts if a.company_id]
    company_map: dict[int, tuple[str, int]] = {}
    if company_ids:
        cres = await db.execute(
            select(Company.id, Company.denumire, Company.cui).where(Company.id.in_(company_ids))
        )
        for row in cres.all():
            company_map[row.id] = (row.denumire, row.cui)

    out = []
    for a in alerts:
        d = AlertSchema.model_validate(a).model_dump()
        cname, ccui = company_map.get(a.company_id, (None, None)) if a.company_id else (None, None)
        d["company_name"] = cname
        d["company_cui"] = ccui
        out.append(d)
    return out


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Get count of unread alerts."""
    result = await db.execute(
        select(func.count(Alert.id))
        .where(and_(Alert.user_id == user.sub, Alert.citita == False))
    )
    return {"unread": result.scalar() or 0}


@router.put("/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Mark a single alert as read."""
    result = await db.execute(
        select(Alert).where(and_(Alert.id == alert_id, Alert.user_id == user.sub))
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.citita = True
    await db.commit()
    return {"status": "ok"}


@router.put("/mark-all-read")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """Mark all alerts as read for current user."""
    await db.execute(
        update(Alert)
        .where(and_(Alert.user_id == user.sub, Alert.citita == False))
        .values(citita=True)
    )
    await db.commit()
    return {"status": "ok"}


@router.get("/types")
async def alert_types(user: TokenPayload = Depends(get_current_user)):
    """List all available alert types."""
    return [
        {"code": "fiscal_status_change", "label": "Schimbare stare fiscală"},
        {"code": "insolvency_opened", "label": "Deschidere insolvență"},
        {"code": "new_court_case", "label": "Dosar judiciar nou"},
        {"code": "financial_data_published", "label": "Bilanț publicat"},
        {"code": "administrator_change", "label": "Schimbare administrator"},
        {"code": "associates_change", "label": "Schimbare asociați"},
        {"code": "new_public_contract", "label": "Contract public nou"},
        {"code": "risk_score_degraded", "label": "Degradare scor risc"},
        {"code": "address_change", "label": "Schimbare sediu"},
        {"code": "caen_change", "label": "Schimbare CAEN"},
        {"code": "new_mo_mention", "label": "Mențiune Monitor Oficial"},
        {"code": "debt_status_change", "label": "Schimbare stare datorii"},
        {"code": "esg_score_change", "label": "Schimbare scor ESG"},
    ]


# ── 5.5: Alert Analytics ──

@router.get("/analytics")
async def alert_analytics(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """5.5: Alert analytics — counts, trends, top companies."""
    from app.services.alerts_service import AlertService
    svc = AlertService(db)
    return await svc.get_analytics(user_id=user.sub, days=days)


@router.get("/grouped")
async def grouped_alerts(
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """5.3: Unread alerts grouped by company."""
    from app.services.alerts_service import AlertService
    svc = AlertService(db)
    return await svc.get_grouped_alerts(user_id=user.sub, limit=limit)


# ── 5.2: User Alert Preferences ──

@router.get("/preferences")
async def get_alert_preferences(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """5.2: Get current user alert preferences."""
    result = await db.execute(select(User.alert_preferences).where(User.id == _to_uuid(user.sub)))
    prefs = result.scalar_one_or_none()
    return prefs or {"disabled_types": [], "channels": ["websocket"]}


@router.put("/preferences")
async def update_alert_preferences(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """
    5.2: Update user alert preferences.
    Body: {
        "disabled_types": ["new_mo_mention"],
        "channels": ["websocket", "email"],
        "webhook_url": "https://...",
        "slack_webhook": "https://hooks.slack.com/..."
    }
    """
    from app.services.alerts_service import ALERT_TYPES as AT
    disabled = body.get("disabled_types", [])
    if any(t not in AT for t in disabled):
        raise HTTPException(status_code=400, detail="Invalid alert type in disabled_types")

    valid_channels = {"websocket", "email", "sms", "webhook", "slack"}
    channels = body.get("channels", ["websocket"])
    if any(c not in valid_channels for c in channels):
        raise HTTPException(status_code=400, detail="Invalid channel")

    prefs = {
        "disabled_types": disabled,
        "channels": channels,
        "webhook_url": body.get("webhook_url"),
        "slack_webhook": body.get("slack_webhook"),
    }

    result = await db.execute(select(User).where(User.id == _to_uuid(user.sub)))
    u = result.scalar_one_or_none()
    if u:
        u.alert_preferences = prefs
        await db.commit()

    return prefs
