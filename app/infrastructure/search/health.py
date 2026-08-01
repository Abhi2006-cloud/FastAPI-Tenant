import logging
from app.infrastructure.search.client import search_client

logger = logging.getLogger(__name__)

async def check_search_health() -> str:
    """Check Meilisearch health status. Returns 'connected' or 'unavailable'."""
    try:
        return await search_client.health_status()
    except Exception as e:
        logger.warning("Error checking Meilisearch health: %s", str(e))
        return "unavailable"
