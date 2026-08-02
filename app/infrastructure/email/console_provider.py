"""Console Email Provider (Zero-Quota Local Development)."""

import logging
import uuid
from typing import Any, Dict

from app.core.config import get_settings
from app.infrastructure.email.provider import EmailProvider

logger = logging.getLogger(__name__)


class ConsoleProvider(EmailProvider):
    """Console email provider. Renders templates and logs details cleanly to stdout/logger."""

    @property
    def name(self) -> str:
        return "console"

    def validate_configuration(self) -> bool:
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
        settings = get_settings()
        sender_name = from_name or settings.email_from_name
        sender_addr = from_address or settings.email_from_address
        message_id = f"console-{uuid.uuid4()}"

        border = "=" * 60
        log_output = (
            f"\n{border}\n"
            f"📧 [CONSOLE EMAIL PROVIDER]\n"
            f"From:    {sender_name} <{sender_addr}>\n"
            f"To:      {to}\n"
            f"Subject: {subject}\n"
            f"ID:      {message_id}\n"
            f"{'-' * 60}\n"
            f"[PLAIN TEXT BODY]\n"
            f"{text_content}\n"
            f"{'-' * 60}\n"
            f"[HTML CONTENT PREVIEW]\n"
            f"{html_content[:300]}...\n"
            f"{border}\n"
        )
        logger.info(log_output)

        return {
            "id": message_id,
            "provider": "console",
            "status": "sent",
            "to": to,
            "subject": subject,
        }
