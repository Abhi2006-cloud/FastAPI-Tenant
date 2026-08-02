"""Email Health Monitor with 60-second status caching."""

import logging
import time
from typing import Any, Dict

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Lightweight in-memory health cache
_HEALTH_CACHE: Dict[str, Any] = {
    "status": "unknown",
    "provider": "console",
    "last_checked": 0.0,
    "last_error": None,
}
_CACHE_TTL_SECONDS = 60.0


async def check_email_health(force_refresh: bool = False) -> Dict[str, Any]:
    """Check email provider status with a 60-second in-memory cache to prevent external API overhead."""
    now = time.time()
    if not force_refresh and (now - _HEALTH_CACHE["last_checked"] < _CACHE_TTL_SECONDS):
        return _HEALTH_CACHE

    settings = get_settings()
    mode = settings.effective_email_mode
    provider_name = settings.email_provider.lower()

    if mode == "development":
        _HEALTH_CACHE.update({
            "status": "development",
            "provider": provider_name if provider_name != "console" else "console",
            "email_mode": "development",
            "last_checked": now,
            "last_error": None,
            "detail": "Development mode active. Manual invitation links provided in responses/logs.",
        })
        return _HEALTH_CACHE

    if mode == "console":
        _HEALTH_CACHE.update({
            "status": "console",
            "provider": "console",
            "email_mode": "console",
            "last_checked": now,
            "last_error": None,
            "detail": "Console mode active (zero API quota consumption)",
        })
        return _HEALTH_CACHE

    if provider_name == "resend":
        key = settings.resend_api_key
        if not key or key.startswith("<") or key == "RESEND_API_KEY":
            _HEALTH_CACHE.update({
                "status": "misconfigured",
                "provider": "resend",
                "email_mode": "production",
                "last_checked": now,
                "last_error": "RESEND_API_KEY is not set or contains placeholder",
                "detail": "Resend API key missing",
            })
            return _HEALTH_CACHE

        _HEALTH_CACHE.update({
            "status": "connected",
            "provider": "resend",
            "email_mode": "production",
            "last_checked": now,
            "last_error": None,
            "detail": "Resend API configured and ready for production delivery",
        })
        return _HEALTH_CACHE

    _HEALTH_CACHE.update({
        "status": "unknown_provider",
        "provider": provider_name,
        "email_mode": mode,
        "last_checked": now,
        "last_error": f"Unknown email provider: {provider_name}",
        "detail": f"Provider '{provider_name}' is unsupported",
    })
    return _HEALTH_CACHE
