"""
Notification Celery tasks — email, SMS delivery.
"""
from __future__ import annotations

import asyncio

from app.tasks.celery_app import celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.notification_tasks.send_alert_email")
def send_alert_email(user_id: str, alert_id: int):
    """Send alert notification via email."""

    async def _run():
        from app.models.models import User, Alert
        from sqlalchemy import select

        async with get_db_context() as db:
            import uuid
            user_result = await db.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return {"error": "User not found"}

            alert_result = await db.execute(
                select(Alert).where(Alert.id == alert_id)
            )
            alert = alert_result.scalar_one_or_none()
            if not alert:
                return {"error": "Alert not found"}

            # Send email via SMTP
            from app.core.config import settings

            if not settings.SMTP_HOST:
                logger.warning("smtp_not_configured")
                return {"error": "SMTP not configured"}

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_FROM or "noreply@rombiz.ro"
            msg["To"] = user.email
            msg["Subject"] = f"RomBiz Alert: {alert.tip_alerta}"

            body = f"""
            <h2>Notificare RomBiz Intelligence</h2>
            <p><strong>Tip:</strong> {alert.tip_alerta}</p>
            <p><strong>Mesaj:</strong> {alert.titlu}</p>
            <p><a href="https://app.rombiz.ro/alerts/{alert.id}">Vezi detalii</a></p>
            """
            msg.attach(MIMEText(body, "html"))

            try:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT or 587) as server:
                    server.starttls()
                    if settings.SMTP_USER and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)

                logger.info("alert_email_sent", user_id=user_id, alert_id=alert_id)
                return {"status": "sent"}

            except Exception as e:
                logger.error("alert_email_failed", error=str(e))
                return {"error": str(e)}

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.notification_tasks.send_alert_sms")
def send_alert_sms(user_id: str, alert_id: int):
    """5.4: Send alert notification via SMS using Twilio."""

    async def _run():
        from app.models.models import User, Alert
        from sqlalchemy import select

        async with get_db_context() as db:
            import uuid
            user_result = await db.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return {"error": "User not found"}

            alert_result = await db.execute(
                select(Alert).where(Alert.id == alert_id)
            )
            alert = alert_result.scalar_one_or_none()
            if not alert:
                return {"error": "Alert not found"}

            from app.core.config import settings

            twilio_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "") or ""
            twilio_token = getattr(settings, "TWILIO_AUTH_TOKEN", "") or ""
            twilio_from = getattr(settings, "TWILIO_FROM_NUMBER", "") or ""

            if not twilio_sid or not twilio_token or not twilio_from:
                logger.warning("twilio_not_configured")
                return {"status": "skipped", "message": "Twilio not configured"}

            # Get user phone — try telefon field or fallback
            user_phone = getattr(user, "telefon", None) or getattr(user, "phone_number", None)
            if not user_phone:
                logger.warning("user_no_phone", user_id=user_id)
                return {"status": "skipped", "message": "User has no phone number"}

            sms_body = f"RomBiz Alert: {alert.titlu or alert.tip_alerta}"

            try:
                from twilio.rest import Client
                client = Client(twilio_sid, twilio_token)
                message = client.messages.create(
                    body=sms_body,
                    from_=twilio_from,
                    to=user_phone,
                )
                logger.info("sms_sent", user_id=user_id, alert_id=alert_id, sid=message.sid)
                return {"status": "sent", "message_sid": message.sid}

            except ImportError:
                logger.error("twilio_package_not_installed")
                return {"status": "error", "message": "twilio package not installed (pip install twilio)"}
            except Exception as e:
                logger.error("sms_send_failed", error=str(e), user_id=user_id)
                return {"status": "error", "message": str(e)}

    return asyncio.run(_run())


@celery_app.task(name="app.tasks.notification_tasks.send_alert_webhook")
def send_alert_webhook(webhook_url: str, payload: dict):
    """5.4: Send alert to custom webhook URL."""
    import requests

    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json", "User-Agent": "RomBiz-Alerts/2.0"},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("webhook_sent", url=webhook_url, status=resp.status_code)
        return {"status": "sent", "status_code": resp.status_code}
    except requests.RequestException as e:
        logger.error("webhook_failed", url=webhook_url, error=str(e))
        return {"error": str(e)}


@celery_app.task(name="app.tasks.notification_tasks.send_alert_slack")
def send_alert_slack(webhook_url: str, message: str):
    """5.4: Send alert to Slack channel via incoming webhook."""
    import requests

    try:
        resp = requests.post(
            webhook_url,
            json={"text": message},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("slack_sent", status=resp.status_code)
        return {"status": "sent"}
    except requests.RequestException as e:
        logger.error("slack_failed", error=str(e))
        return {"error": str(e)}
