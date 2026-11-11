import logging
from app.core.config import get_settings
from app.infrastructure.search.client import search_client

logger = logging.getLogger(__name__)

async def check_search_health() -> str:
    """Check Meilisearch health status. Returns 'connected', 'disabled', or 'unavailable'."""
    settings = get_settings()
    if not settings.is_search_enabled:
        return "disabled"
    try:
        return await search_client.health_status()
    except Exception as e:
        logger.warning("Error checking Meilisearch health: %s", str(e))
        return "unavailable"
