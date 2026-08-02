"""Resend Email Provider (Production API Integration)."""

import logging
from typing import Any, Dict

import httpx

from app.core.config import get_settings
from app.infrastructure.email.exceptions import (
    EmailConfigurationException,
    EmailDeliveryException,
)
from app.infrastructure.email.provider import EmailProvider

logger = logging.getLogger(__name__)


class ResendProvider(EmailProvider):
    """Resend email provider sending HTML & Plain Text emails via https://api.resend.com/emails."""

    @property
    def name(self) -> str:
        return "resend"

    def validate_configuration(self) -> bool:
        settings = get_settings()
        key = settings.resend_api_key
        if not key or key.startswith("<") or key == "RESEND_API_KEY":
            return False
        return True

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html_content: str,
        text_content: str,
        from_name: str | None = None,
        from_address: str | None = None,
    ) -> Dict[str, Any]:
        if not self.validate_configuration():
            raise EmailConfigurationException(
                "Resend API key is missing or invalid. Set RESEND_API_KEY in .env."
            )

        settings = get_settings()
        sender_name = from_name or settings.email_from_name
        sender_addr = from_address or settings.email_from_address
        from_header = f"{sender_name} <{sender_addr}>"

        payload = {
            "from": from_header,
            "to": [to],
            "subject": subject,
            "html": html_content,
            "text": text_content,
        }

        headers = {
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    json=payload,
                    headers=headers,
                )

            if response.status_code >= 400:
                error_detail = response.text
                logger.error("Resend API error [%s]: %s", response.status_code, error_detail)
                raise EmailDeliveryException(
                    f"Resend API error ({response.status_code}): {error_detail}"
                )

            data = response.json()
            logger.info("Email delivered via Resend API to %s, message_id=%s", to, data.get("id"))
            return {
                "id": data.get("id", ""),
                "provider": "resend",
                "status": "sent",
                "response": data,
            }

        except httpx.HTTPError as exc:
            logger.error("Network error delivering email via Resend to %s: %s", to, exc)
            raise EmailDeliveryException(f"Network error connecting to Resend: {str(exc)}") from exc
