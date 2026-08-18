"""
delivery_keywords.py — WhatsApp / SMS delivery keyword.

``Send WhatsApp Digest`` checks consent before every call — a hard-fail
(not a silent skip) if consent is False, because a silent skip would hide
a consent-tracking bug.

Keyword name matches 05_ROBOT_FRAMEWORK_SPEC.md exactly.
"""
import os
import sys
from pathlib import Path

from robot.api import logger
from robot.api.deco import keyword, library

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_DIGEST_TEMPLATE = (
    "*Genuine RX — Your Medicine Price Update*\n\n"
    "{items_text}\n\n"
    "_Reply STOP to unsubscribe. Always confirm substitutes with your pharmacist._"
)

_ITEM_LINE = "- *{brand_name}* ({form}): Rs.{price:.2f}  [{source}]"


@library(scope="SUITE", auto_keywords=False)
class DeliveryKeywords:
    """Keyword library for Twilio-based WhatsApp/SMS delivery."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("Send WhatsApp Digest")
    def send_whatsapp_digest(self, user_id: int, items: list[dict]) -> None:
        """Send a WhatsApp digest to the user identified by *user_id*.

        Behaviour:
        - Looks up the user's phone and ``consent_whatsapp`` from the DB.
        - Hard-fails (raises) if ``consent_whatsapp`` is False — this is
          intentional: a silent skip would allow consent bugs to go undetected.
        - Formats *items* into the standard Genuine RX digest template.
        - Calls Twilio's WhatsApp API using ``GENUINE_RX_TWILIO_*`` env vars.

        Args:
            user_id: Row ID from the ``users`` table.
            items:   List of dicts, each with at least: brand_name, form,
                     price, source.  Typically the output of
                     ``Match Salt To Substitutes``.
        """
        db_url = os.environ.get("GENUINE_RX_DB_URL")
        if not db_url:
            raise RuntimeError("GENUINE_RX_DB_URL is not set.")

        # ---- Fetch user record ----------------------------------------- #
        import psycopg
        dsn = db_url.replace("postgresql+psycopg://", "postgresql://")

        with psycopg.connect(dsn) as conn:
            row = conn.execute(
                "SELECT phone, consent_whatsapp FROM users WHERE user_id = %s",
                (user_id,),
            ).fetchone()

        if row is None:
            raise ValueError(f"User {user_id} not found in database.")

        phone, consent = row[0], row[1]

        # Hard-fail on missing consent — do NOT silently skip
        if not consent:
            raise RuntimeError(
                f"User {user_id} ({phone}) has consent_whatsapp=False. "
                "Cannot send digest. Fix the consent record before retrying."
            )

        # ---- Build message ---------------------------------------------- #
        items_text = "\n".join(
            _ITEM_LINE.format(
                brand_name=item.get("brand_name", "Unknown"),
                form=item.get("form", ""),
                price=float(item.get("price", 0)),
                source=item.get("source", ""),
            )
            for item in items
        )
        body = _DIGEST_TEMPLATE.format(items_text=items_text)

        # ---- Send via Twilio -------------------------------------------- #
        account_sid = os.environ.get("GENUINE_RX_TWILIO_ACCOUNT_SID")
        auth_token  = os.environ.get("GENUINE_RX_TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("GENUINE_RX_TWILIO_FROM_NUMBER", "whatsapp:+14155238886")

        if not account_sid or not auth_token:
            raise RuntimeError(
                "GENUINE_RX_TWILIO_ACCOUNT_SID and GENUINE_RX_TWILIO_AUTH_TOKEN must be set."
            )

        try:
            from twilio.rest import Client  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "twilio package is not installed. Run: pip install -r requirements-core.txt"
            ) from exc

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=from_number,
            to=f"whatsapp:{phone}",
            body=body,
        )

        logger.info(
            f"WhatsApp digest sent to user {user_id} ({phone}). "
            f"Twilio SID: {message.sid}"
        )
