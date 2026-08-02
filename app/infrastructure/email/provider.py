"""Abstract Email Provider Base Class."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class EmailProvider(ABC):
    """Abstract interface for all email providers (Console, Resend, AWS SES, SendGrid)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return provider identifier name (e.g. 'console', 'resend')."""
        pass

    @abstractmethod
    def validate_configuration(self) -> bool:
        """Validate if settings/credentials required for this provider are present."""
        pass

    @abstractmethod
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
        """Send an email delivering both HTML and Plain Text versions.

        Returns provider response payload (must include 'message_id' or 'id').
        """
        pass
