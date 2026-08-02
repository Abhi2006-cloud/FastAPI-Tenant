"""Email Provider Factory and Client Wrapper."""

import logging

from app.core.config import get_settings
from app.infrastructure.email.console_provider import ConsoleProvider
from app.infrastructure.email.provider import EmailProvider
from app.infrastructure.email.resend_provider import ResendProvider

logger = logging.getLogger(__name__)


def get_email_provider() -> EmailProvider:
    """Return configured EmailProvider instance based on EMAIL_MODE and EMAIL_PROVIDER settings."""
    settings = get_settings()

    if settings.effective_email_mode == "production":
        provider_name = (settings.email_provider or "resend").lower()
        if provider_name == "resend":
            provider = ResendProvider()
            if provider.validate_configuration():
                return provider
            logger.warning(
                "Resend provider selected for production but API key missing/invalid. Falling back to ConsoleProvider."
            )

    return ConsoleProvider()
