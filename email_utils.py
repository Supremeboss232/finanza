# email_utils.py
# Non-blocking async email delivery supporting HTTP Email APIs (Resend, SendGrid, Mailtrap)
# and async SMTP (aiosmtplib) with thread-offloaded smtplib fallback.

import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Union

import httpx
from config import settings

log = logging.getLogger(__name__)


def _normalize_recipients(recipients: Union[List[str], str]) -> List[str]:
    if isinstance(recipients, str):
        return [r.strip() for r in recipients.split(",") if r.strip()]
    return [str(r).strip() for r in recipients if r]


async def _send_via_resend(api_key: str, subject: str, recipients: List[str], body: str, subtype: str) -> dict:
    from_addr = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
    payload = {
        "from": from_addr,
        "to": recipients,
        "subject": subject,
    }
    if subtype == "html":
        payload["html"] = body
    else:
        payload["text"] = body

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code in (200, 201, 202):
            log.info("[OK] Email sent via Resend HTTP API to %s", recipients)
            return {"success": True, "provider": "resend", "message": f"Email sent to {recipients}"}
        raise RuntimeError(f"Resend API returned HTTP {resp.status_code}: {resp.text}")


async def _send_via_sendgrid(api_key: str, subject: str, recipients: List[str], body: str, subtype: str) -> dict:
    mime_type = "text/html" if subtype == "html" else "text/plain"
    payload = {
        "personalizations": [{"to": [{"email": r} for r in recipients]}],
        "from": {"email": settings.MAIL_FROM, "name": settings.MAIL_FROM_NAME},
        "subject": subject,
        "content": [{"type": mime_type, "value": body}],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code in (200, 201, 202):
            log.info("[OK] Email sent via SendGrid HTTP API to %s", recipients)
            return {"success": True, "provider": "sendgrid", "message": f"Email sent to {recipients}"}
        raise RuntimeError(f"SendGrid API returned HTTP {resp.status_code}: {resp.text}")


async def _send_via_mailtrap(api_key: str, subject: str, recipients: List[str], body: str, subtype: str) -> dict:
    payload = {
        "from": {
            "email": getattr(settings, "MAILTRAP_FROM_EMAIL", settings.MAIL_FROM),
            "name": getattr(settings, "MAILTRAP_FROM_NAME", settings.MAIL_FROM_NAME),
        },
        "to": [{"email": r} for r in recipients],
        "subject": subject,
    }
    if subtype == "html":
        payload["html"] = body
    else:
        payload["text"] = body

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://send.api.mailtrap.io/api/send",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code in (200, 201, 202):
            log.info("[OK] Email sent via Mailtrap HTTP API to %s", recipients)
            return {"success": True, "provider": "mailtrap", "message": f"Email sent to {recipients}"}
        raise RuntimeError(f"Mailtrap API returned HTTP {resp.status_code}: {resp.text}")


def _build_mime_message(subject: str, recipients: List[str], body: str, subtype: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body, "html" if subtype == "html" else "plain", "utf-8"))
    return msg


def _sync_smtp_send(msg: MIMEMultipart, recipients: List[str]) -> None:
    with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT, timeout=10) as server:
        if settings.MAIL_STARTTLS:
            server.starttls()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.sendmail(settings.MAIL_FROM, recipients, msg.as_string())


async def _send_via_async_smtp(subject: str, recipients: List[str], body: str, subtype: str) -> dict:
    msg = _build_mime_message(subject, recipients, body, subtype)
    try:
        import aiosmtplib

        await aiosmtplib.send(
            msg,
            hostname=settings.MAIL_SERVER,
            port=settings.MAIL_PORT,
            username=settings.MAIL_USERNAME,
            password=settings.MAIL_PASSWORD,
            start_tls=bool(settings.MAIL_STARTTLS),
            use_tls=bool(settings.MAIL_SSL_TLS),
            timeout=10.0,
        )
        log.info("[OK] Email sent via aiosmtplib to %s", recipients)
        return {"success": True, "provider": "aiosmtplib", "message": f"Email sent to {recipients}"}
    except ImportError:
        await asyncio.to_thread(_sync_smtp_send, msg, recipients)
        log.info("[OK] Email sent via threaded SMTP to %s", recipients)
        return {"success": True, "provider": "smtp_thread", "message": f"Email sent to {recipients}"}


async def send_email(subject: str, recipients: list, body: str, subtype: str = "html"):
    """
    Send email non-blockingly using the best configured provider:
    1. Resend HTTP API (RESEND_API_KEY) — port 443, cloud-firewall safe
    2. SendGrid HTTP API (SENDGRID_API_KEY) — port 443, cloud-firewall safe
    3. Mailtrap HTTP API (MAILTRAP_TOKEN) — port 443, cloud-firewall safe
    4. Async SMTP (aiosmtplib / Gmail SMTP) — non-blocking async TLS
    """
    recips = _normalize_recipients(recipients)
    if not recips:
        return {"success": False, "message": "No recipients specified"}

    # 1. Try Resend HTTP API if configured
    resend_key = os.environ.get("RESEND_API_KEY") or getattr(settings, "RESEND_API_KEY", None)
    if resend_key:
        try:
            return await _send_via_resend(resend_key, subject, recips, body, subtype)
        except Exception as e:
            log.warning("[EMAIL] Resend HTTP API failed, falling back: %s", e)

    # 2. Try SendGrid HTTP API if configured
    sendgrid_key = os.environ.get("SENDGRID_API_KEY") or getattr(settings, "SENDGRID_API_KEY", None)
    if sendgrid_key:
        try:
            return await _send_via_sendgrid(sendgrid_key, subject, recips, body, subtype)
        except Exception as e:
            log.warning("[EMAIL] SendGrid HTTP API failed, falling back: %s", e)

    # 3. Try Mailtrap HTTP API if configured
    mailtrap_key = os.environ.get("MAILTRAP_TOKEN") or getattr(settings, "MAILTRAP_TOKEN", None)
    if mailtrap_key:
        try:
            return await _send_via_mailtrap(mailtrap_key, subject, recips, body, subtype)
        except Exception as e:
            log.warning("[EMAIL] Mailtrap HTTP API failed, falling back: %s", e)

    # 4. Try Async SMTP (Gmail / custom SMTP)
    if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
        try:
            return await _send_via_async_smtp(subject, recips, body, subtype)
        except Exception as e:
            log.error("[FAIL] Async SMTP email delivery failed to %s: %s", recips, e)
            raise

    log.warning("[WARN] No email provider credentials configured (RESEND_API_KEY, SENDGRID_API_KEY, or MAIL_USERNAME/MAIL_PASSWORD)")
    raise ValueError("Email provider credentials not configured in environment")
