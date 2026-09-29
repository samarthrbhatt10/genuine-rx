"""
mailer.py — tiny email sender with a zero-config demo mode.

* If GENUINE_RX_SMTP_USER and GENUINE_RX_SMTP_PASSWORD are set, the email is
  sent for real over SMTP (defaults work for Gmail with an "App Password").
* Otherwise the email is written to rpa/outbox/*.html so the bot can be
  demonstrated with no mail account at all.

Environment variables (all optional):
    GENUINE_RX_SMTP_USER      login / sender address, e.g. you@gmail.com
    GENUINE_RX_SMTP_PASSWORD  Gmail App Password (not your normal password)
    GENUINE_RX_SMTP_HOST      default smtp.gmail.com
    GENUINE_RX_SMTP_PORT      default 465 (SSL); 587 uses STARTTLS
"""
import os
import re
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

OUTBOX_DIR = Path(__file__).resolve().parents[1] / "outbox"


class MailError(RuntimeError):
    """Raised when a real SMTP send fails."""


def smtp_configured() -> bool:
    return bool(os.environ.get("GENUINE_RX_SMTP_USER") and os.environ.get("GENUINE_RX_SMTP_PASSWORD"))


def send_email(to: str, subject: str, html: str, text: str) -> dict:
    """Send (or save) one email. Returns {"mode": "smtp"|"outbox", "path": str|None}."""
    if not smtp_configured():
        return {"mode": "outbox", "path": str(_save_to_outbox(to, subject, html))}

    user = os.environ["GENUINE_RX_SMTP_USER"]
    password = os.environ["GENUINE_RX_SMTP_PASSWORD"].replace(" ", "")  # Gmail shows it with spaces
    host = os.environ.get("GENUINE_RX_SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("GENUINE_RX_SMTP_PORT", "465"))

    msg = EmailMessage()
    msg["From"] = f"Genuine RX Alerts <{user}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=20) as s:
                s.login(user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(user, password)
                s.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise MailError(f"SMTP send to {to} failed: {exc}") from exc
    return {"mode": "smtp", "path": None}


def _save_to_outbox(to: str, subject: str, html: str) -> Path:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    slug = re.sub(r"[^a-z0-9]+", "-", to.lower()).strip("-")
    path = OUTBOX_DIR / f"{stamp}_{slug}.html"
    header = (
        f"<!-- To: {to} | Subject: {subject} -->\n"
        f"<div style='font:12px monospace;background:#fffbe6;padding:8px;border-bottom:1px solid #ddd'>"
        f"<b>DEMO OUTBOX</b> (no SMTP configured) &mdash; To: {to} &mdash; Subject: {subject}</div>\n"
    )
    path.write_text(header + html, encoding="utf-8")
    return path
