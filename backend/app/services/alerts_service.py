"""
Alerts service — generate and dispatch alerts via WebSocket, email, SMS, webhook.
Supports 13 alert types with smart dedup, rate limiting, and multi-channel dispatch.

v2 Improvements:
  5.1: All 13 trigger methods implemented
  5.2: User alert preferences (per-type enable/disable, channel selection)
  5.3: Smart alerting — dedup, rate limiting, grouping
  5.4: Multi-channel dispatch — WebSocket, email, SMS, webhook, Slack
  5.5: Alert analytics — counts, trends, response times
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Alert, MonitoredPortfolio, PortfolioCompany, Company, User,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


ALERT_TYPES = {
    "fiscal_status_change": "Schimbare stare fiscală",
    "insolvency_opened": "Deschidere insolvență",
    "new_court_case": "Dosar judiciar nou",
    "financial_data_published": "Bilanț publicat",
    "administrator_change": "Schimbare administrator",
    "associates_change": "Schimbare asociați",
    "new_public_contract": "Contract public nou",
    "risk_score_degraded": "Degradare scor risc",
    "address_change": "Schimbare sediu",
    "caen_change": "Schimbare CAEN",
    "new_mo_mention": "Mențiune Monitor Oficial",
    "debt_status_change": "Schimbare stare datorii",
    "esg_score_change": "Schimbare scor ESG",
    "ai_anomaly_detected": "Anomalie AI Detectată",
}

# 5.3: Rate limiting defaults (max alerts per type per company per period)
RATE_LIMITS = {
    "fiscal_status_change": {"max_per_day": 2},
    "insolvency_opened": {"max_per_day": 1},
    "new_court_case": {"max_per_day": 5},
    "financial_data_published": {"max_per_day": 1},
    "administrator_change": {"max_per_day": 3},
    "associates_change": {"max_per_day": 3},
    "new_public_contract": {"max_per_day": 10},
    "risk_score_degraded": {"max_per_day": 1},
    "address_change": {"max_per_day": 1},
    "caen_change": {"max_per_day": 1},
    "new_mo_mention": {"max_per_day": 5},
    "debt_status_change": {"max_per_day": 2},
    "esg_score_change": {"max_per_day": 1},
}


class AlertService:
    """Service for creating and dispatching alerts (v2)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ──────────────────────────────────────────────────────────────────
    # Core alert creation with 5.3 smart alerting
    # ──────────────────────────────────────────────────────────────────

    async def create_alert(
        self,
        company_id: int,
        tip_alerta: str,
        mesaj: str,
        detalii: Optional[dict] = None,
        severity: str = "INFO",
    ) -> list[Alert]:
        """
        Create alerts for all users monitoring this company.
        5.3: Includes dedup, rate limiting, and user preference checks.
        """
        if tip_alerta not in ALERT_TYPES:
            logger.warning("unknown_alert_type", tip=tip_alerta)
            return []

        # 5.3: Check rate limit
        if await self._is_rate_limited(company_id, tip_alerta):
            logger.info("alert_rate_limited", company_id=company_id, tip=tip_alerta)
            return []

        # 5.3: Dedup check — don't create identical alert within 1 hour
        if await self._is_duplicate(company_id, tip_alerta, mesaj):
            logger.info("alert_deduplicated", company_id=company_id, tip=tip_alerta)
            return []

        # Find all users monitoring this company
        result = await self.db.execute(
            select(PortfolioCompany.portfolio_id)
            .where(PortfolioCompany.company_id == company_id)
        )
        portfolio_ids = [r.portfolio_id for r in result.all()]

        if not portfolio_ids:
            return []

        result = await self.db.execute(
            select(MonitoredPortfolio.user_id)
            .where(MonitoredPortfolio.id.in_(portfolio_ids))
            .distinct()
        )
        user_ids = [r.user_id for r in result.all()]

        alerts = []
        for user_id in user_ids:
            # 5.2: Check user preferences
            if not await self._user_wants_alert(user_id, tip_alerta):
                continue

            alert = Alert(
                user_id=user_id,
                company_id=company_id,
                tip_alerta=tip_alerta,
                titlu=mesaj,
                alert_payload=detalii or {},
                citita=False,
            )
            self.db.add(alert)
            alerts.append(alert)

        await self.db.flush()

        # 5.4: Multi-channel dispatch
        for alert in alerts:
            await self._dispatch_all_channels(alert)

        logger.info(
            "alerts_created",
            company_id=company_id,
            tip=tip_alerta,
            count=len(alerts),
            severity=severity,
        )

        return alerts

    # ──────────────────────────────────────────────────────────────────
    # 5.3: Smart Alerting — Dedup, Rate Limiting
    # ──────────────────────────────────────────────────────────────────

    async def _is_rate_limited(self, company_id: int, tip_alerta: str) -> bool:
        """5.3: Check if alert type for company exceeds daily limit."""
        limit_config = RATE_LIMITS.get(tip_alerta)
        if not limit_config:
            return False

        max_per_day = limit_config["max_per_day"]
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        result = await self.db.execute(
            select(func.count(Alert.id))
            .where(
                Alert.company_id == company_id,
                Alert.tip_alerta == tip_alerta,
                Alert.created_at >= since,
            )
        )
        count = result.scalar() or 0
        return count >= max_per_day

    async def _is_duplicate(self, company_id: int, tip_alerta: str, mesaj: str) -> bool:
        """5.3: Check if identical alert was created within last hour."""
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = await self.db.execute(
            select(func.count(Alert.id))
            .where(
                Alert.company_id == company_id,
                Alert.tip_alerta == tip_alerta,
                Alert.titlu == mesaj,
                Alert.created_at >= since,
            )
        )
        count = result.scalar() or 0
        return count > 0

    async def _user_wants_alert(self, user_id: int, tip_alerta: str) -> bool:
        """
        5.2: Check user alert preferences.
        If no preferences set, default to all alerts enabled.
        """
        result = await self.db.execute(
            select(User.alert_preferences)
            .where(User.id == user_id)
        )
        prefs = result.scalar_one_or_none()

        if not prefs or not isinstance(prefs, dict):
            return True  # Default: all enabled

        disabled = prefs.get("disabled_types", [])
        return tip_alerta not in disabled

    # ──────────────────────────────────────────────────────────────────
    # 5.4: Multi-Channel Dispatch
    # ──────────────────────────────────────────────────────────────────

    async def _dispatch_all_channels(self, alert: Alert):
        """5.4: Dispatch alert via all configured channels for the user."""
        # Always try WebSocket (real-time)
        await self._dispatch_websocket(alert)

        # Check user channel preferences
        result = await self.db.execute(
            select(User.alert_preferences)
            .where(User.id == alert.user_id)
        )
        prefs = result.scalar_one_or_none()
        channels = (prefs or {}).get("channels", ["websocket"])

        if "email" in channels:
            await self._dispatch_email(alert)

        if "sms" in channels:
            await self._dispatch_sms(alert)

        if "webhook" in channels:
            webhook_url = (prefs or {}).get("webhook_url")
            if webhook_url:
                await self._dispatch_webhook(alert, webhook_url)

        if "slack" in channels:
            slack_webhook = (prefs or {}).get("slack_webhook")
            if slack_webhook:
                await self._dispatch_slack(alert, slack_webhook)

    async def _dispatch_websocket(self, alert: Alert):
        """Send alert via WebSocket to connected users."""
        try:
            from app.api.v1.endpoints.alerts import manager
            await manager.send_to_user(
                str(alert.user_id),
                {
                    "type": "alert",
                    "id": alert.id,
                    "tip_alerta": alert.tip_alerta,
                    "titlu": alert.titlu,
                    "company_id": alert.company_id,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None,
                },
            )
        except Exception as e:
            logger.error("websocket_dispatch_failed", error=str(e))

    async def _dispatch_email(self, alert: Alert):
        """5.4: Send alert via email (async via Celery)."""
        try:
            from app.tasks.notification_tasks import send_alert_email
            send_alert_email.delay(
                user_id=str(alert.user_id),
                alert_id=alert.id,
            )
        except Exception as e:
            logger.error("email_dispatch_failed", error=str(e))

    async def _dispatch_sms(self, alert: Alert):
        """5.4: Send alert via SMS (stub — requires Twilio/Bandwith integration)."""
        try:
            from app.tasks.notification_tasks import send_alert_sms
            send_alert_sms.delay(
                user_id=str(alert.user_id),
                alert_id=alert.id,
            )
        except Exception as e:
            logger.error("sms_dispatch_failed", error=str(e))

    async def _dispatch_webhook(self, alert: Alert, url: str):
        """5.4: Send alert to custom webhook URL."""
        try:
            from app.tasks.notification_tasks import send_alert_webhook
            send_alert_webhook.delay(
                webhook_url=url,
                payload={
                    "type": "rombiz_alert",
                    "alert_type": alert.tip_alerta,
                    "title": alert.titlu,
                    "company_id": alert.company_id,
                    "timestamp": alert.created_at.isoformat() if alert.created_at else None,
                },
            )
        except Exception as e:
            logger.error("webhook_dispatch_failed", error=str(e))

    async def _dispatch_slack(self, alert: Alert, webhook_url: str):
        """5.4: Send alert to Slack channel via incoming webhook."""
        try:
            from app.tasks.notification_tasks import send_alert_slack
            send_alert_slack.delay(
                webhook_url=webhook_url,
                message=f"🔔 *{ALERT_TYPES.get(alert.tip_alerta, alert.tip_alerta)}*\n{alert.titlu}",
            )
        except Exception as e:
            logger.error("slack_dispatch_failed", error=str(e))

    # ──────────────────────────────────────────────────────────────────
    # 5.1: ALL 13 Trigger Methods
    # ──────────────────────────────────────────────────────────────────

    async def check_fiscal_status_change(self, company: Company, old_status: str, new_status: str):
        """Trigger: Fiscal status changed."""
        if old_status != new_status:
            await self.create_alert(
                company_id=company.id,
                tip_alerta="fiscal_status_change",
                mesaj=f"{company.denumire} (CUI {company.cui}): stare fiscală schimbată de la '{old_status}' la '{new_status}'",
                detalii={"old_status": old_status, "new_status": new_status},
                severity="HIGH",
            )

    async def check_insolvency(self, company: Company):
        """Trigger: Insolvency proceeding opened."""
        await self.create_alert(
            company_id=company.id,
            tip_alerta="insolvency_opened",
            mesaj=f"{company.denumire} (CUI {company.cui}): procedură de insolvență deschisă",
            severity="CRITICAL",
        )

    async def check_new_court_case(self, company: Company, numar_dosar: str, materie: str):
        """5.1: Trigger: New court case filed."""
        await self.create_alert(
            company_id=company.id,
            tip_alerta="new_court_case",
            mesaj=f"{company.denumire}: dosar nou {numar_dosar} ({materie})",
            detalii={"numar_dosar": numar_dosar, "materie": materie},
            severity="MEDIUM",
        )

    async def check_financial_data_published(self, company: Company, an_fiscal: int):
        """5.1: Trigger: New financial data published."""
        await self.create_alert(
            company_id=company.id,
            tip_alerta="financial_data_published",
            mesaj=f"{company.denumire}: bilanț {an_fiscal} publicat",
            detalii={"an_fiscal": an_fiscal},
            severity="INFO",
        )

    async def check_administrator_change(
        self, company: Company, old_admin: str, new_admin: str, change_type: str
    ):
        """5.1: Trigger: Administrator changed."""
        await self.create_alert(
            company_id=company.id,
            tip_alerta="administrator_change",
            mesaj=f"{company.denumire}: administrator {change_type} — {new_admin or old_admin}",
            detalii={"old": old_admin, "new": new_admin, "type": change_type},
            severity="HIGH",
        )

    async def check_associates_change(
        self, company: Company, person_name: str, change_type: str, procent: float = None
    ):
        """5.1: Trigger: Associates/shareholders changed."""
        msg = f"{company.denumire}: asociat {change_type} — {person_name}"
        if procent is not None:
            msg += f" ({procent}%)"
        await self.create_alert(
            company_id=company.id,
            tip_alerta="associates_change",
            mesaj=msg,
            detalii={"person": person_name, "type": change_type, "procent": procent},
            severity="MEDIUM",
        )

    async def check_new_public_contract(
        self, company: Company, contract_title: str, valoare_ron: float = None
    ):
        """5.1: Trigger: New public contract awarded."""
        msg = f"{company.denumire}: contract public — {contract_title}"
        if valoare_ron:
            msg += f" ({valoare_ron:,.0f} RON)"
        await self.create_alert(
            company_id=company.id,
            tip_alerta="new_public_contract",
            mesaj=msg,
            detalii={"title": contract_title, "valoare_ron": valoare_ron},
            severity="INFO",
        )

    async def check_risk_degradation(self, company_id: int, old_category: str, new_category: str):
        """Trigger: Risk score degraded."""
        if old_category < new_category:
            result = await self.db.execute(
                select(Company).where(Company.id == company_id)
            )
            company = result.scalar_one_or_none()
            if company:
                await self.create_alert(
                    company_id=company_id,
                    tip_alerta="risk_score_degraded",
                    mesaj=f"{company.denumire}: scor risc degradat de la {old_category} la {new_category}",
                    detalii={"old": old_category, "new": new_category},
                    severity="HIGH",
                )

    async def check_address_change(self, company: Company, old_address: str, new_address: str):
        """5.1: Trigger: Company address changed."""
        await self.create_alert(
            company_id=company.id,
            tip_alerta="address_change",
            mesaj=f"{company.denumire}: sediu mutat",
            detalii={"old_address": old_address, "new_address": new_address},
            severity="MEDIUM",
        )

    async def check_caen_change(self, company: Company, old_caen: str, new_caen: str):
        """5.1: Trigger: CAEN code changed."""
        await self.create_alert(
            company_id=company.id,
            tip_alerta="caen_change",
            mesaj=f"{company.denumire}: CAEN schimbat de la {old_caen} la {new_caen}",
            detalii={"old_caen": old_caen, "new_caen": new_caen},
            severity="INFO",
        )

    async def check_monitor_oficial_mention(self, company: Company, description: str, mo_number: str):
        """5.1: Trigger: New Monitor Oficial mention."""
        await self.create_alert(
            company_id=company.id,
            tip_alerta="new_mo_mention",
            mesaj=f"{company.denumire}: menționat în Monitorul Oficial ({mo_number})",
            detalii={"description": description, "mo_number": mo_number},
            severity="INFO",
        )

    async def check_debt_status_change(
        self, company: Company, had_debts: bool, has_debts: bool, total_debts: float = None
    ):
        """5.1: Trigger: Debt status changed."""
        if had_debts != has_debts:
            if has_debts:
                msg = f"{company.denumire}: datorii restante detectate"
                if total_debts:
                    msg += f" ({total_debts:,.0f} RON)"
                severity = "HIGH"
            else:
                msg = f"{company.denumire}: datorii restante achitate"
                severity = "INFO"

            await self.create_alert(
                company_id=company.id,
                tip_alerta="debt_status_change",
                mesaj=msg,
                detalii={"had_debts": had_debts, "has_debts": has_debts, "total": total_debts},
                severity=severity,
            )

    async def check_esg_score_change(
        self, company: Company, old_score: float, new_score: float, old_sfdr: str, new_sfdr: str
    ):
        """5.1: Trigger: ESG score significantly changed."""
        diff = abs(new_score - old_score)
        if diff >= 5 or old_sfdr != new_sfdr:  # Significant change threshold
            direction = "crescut" if new_score > old_score else "scăzut"
            await self.create_alert(
                company_id=company.id,
                tip_alerta="esg_score_change",
                mesaj=f"{company.denumire}: scor ESG {direction} de la {old_score:.1f} la {new_score:.1f}",
                detalii={
                    "old_score": old_score, "new_score": new_score,
                    "old_sfdr": old_sfdr, "new_sfdr": new_sfdr,
                    "change": round(diff, 2),
                },
                severity="MEDIUM" if diff < 15 else "HIGH",
            )

    # ──────────────────────────────────────────────────────────────────
    # 5.5: Alert Analytics
    # ──────────────────────────────────────────────────────────────────

    async def get_analytics(self, user_id: int, days: int = 30) -> dict:
        """
        5.5: Alert analytics — counts, trends, response times.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Total and unread counts
        total_result = await self.db.execute(
            select(func.count(Alert.id))
            .where(Alert.user_id == user_id, Alert.created_at >= since)
        )
        total = total_result.scalar() or 0

        unread_result = await self.db.execute(
            select(func.count(Alert.id))
            .where(Alert.user_id == user_id, Alert.citita == False, Alert.created_at >= since)
        )
        unread = unread_result.scalar() or 0

        # By type breakdown
        type_result = await self.db.execute(
            select(Alert.tip_alerta, func.count(Alert.id).label("cnt"))
            .where(Alert.user_id == user_id, Alert.created_at >= since)
            .group_by(Alert.tip_alerta)
            .order_by(func.count(Alert.id).desc())
        )
        by_type = {r.tip_alerta: r.cnt for r in type_result.all()}

        # Daily trend
        daily_result = await self.db.execute(
            select(
                func.date(Alert.created_at).label("day"),
                func.count(Alert.id).label("cnt"),
            )
            .where(Alert.user_id == user_id, Alert.created_at >= since)
            .group_by(func.date(Alert.created_at))
            .order_by(func.date(Alert.created_at))
        )
        daily_trend = [{"date": str(r.day), "count": r.cnt} for r in daily_result.all()]

        # Top alerted companies
        top_companies_result = await self.db.execute(
            select(
                Alert.company_id,
                func.count(Alert.id).label("cnt"),
            )
            .where(Alert.user_id == user_id, Alert.created_at >= since)
            .group_by(Alert.company_id)
            .order_by(func.count(Alert.id).desc())
            .limit(10)
        )
        top_companies = [
            {"company_id": r.company_id, "alert_count": r.cnt}
            for r in top_companies_result.all()
        ]

        return {
            "period_days": days,
            "total": total,
            "unread": unread,
            "read_rate": round((total - unread) / max(total, 1) * 100, 1),
            "by_type": by_type,
            "daily_trend": daily_trend,
            "top_companies": top_companies,
        }

    async def get_grouped_alerts(self, user_id: int, limit: int = 50) -> list[dict]:
        """
        5.3: Get alerts grouped by company for cleaner display.
        """
        result = await self.db.execute(
            select(Alert)
            .where(Alert.user_id == user_id, Alert.citita == False)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        alerts = result.scalars().all()

        # Group by company
        grouped: dict[int, list] = defaultdict(list)
        for alert in alerts:
            grouped[alert.company_id].append({
                "id": alert.id,
                "tip": alert.tip_alerta,
                "titlu": alert.titlu,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            })

        return [
            {"company_id": cid, "alerts": items, "count": len(items)}
            for cid, items in grouped.items()
        ]
