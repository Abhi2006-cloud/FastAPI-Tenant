import logging
from typing import Dict, List
from app.core.config import get_settings
from app.infrastructure.search.client import search_client, MeilisearchApiError

logger = logging.getLogger(__name__)

class IndexManager:
    """Manages the creation and settings configuration of Meilisearch indexes."""
    
    @staticmethod
    def get_index_name(base_name: str) -> str:
        settings = get_settings()
        prefix = settings.meilisearch_index_prefix or "ai_workspace"
        return f"{prefix}_{base_name}"

    @staticmethod
    def get_indexes_definitions() -> Dict[str, Dict[str, List[str]]]:
        """Returns map of base index name to its settings (filterable and sortable attributes)."""
        return {
            "organizations": {
                "filterable": ["id"],
                "sortable": ["created_at"]
            },
            "members": {
                "filterable": ["organization_id", "id", "user_id"],
                "sortable": ["created_at"]
            },
            "files": {
                "filterable": ["organization_id", "id"],
                "sortable": ["created_at"]
            },
            "audit_logs": {
                "filterable": ["organization_id", "id", "action"],
                "sortable": ["created_at"]
            }
        }

    @classmethod
    async def initialize_indexes(cls) -> None:
        """Create indexes and apply settings. Called during app startup lifespan."""
        if not search_client.enabled:
            logger.info("Search client is disabled; skipping index initialization.")
            return

        logger.info("Initializing search indexes on Meilisearch...")
        indexes = cls.get_indexes_definitions()
        
        for base_name, config in indexes.items():
            index_uid = cls.get_index_name(base_name)
            try:
                # 1. Check if index exists by calling GET /indexes/{uid}
                exists = True
                try:
                    await search_client.request("GET", f"/indexes/{index_uid}")
                    logger.info("Index '%s' already exists.", index_uid)
                except MeilisearchApiError as e:
                    if e.status_code == 404:
                        exists = False
                    else:
                        raise

                # 2. If it does not exist, create it
                if not exists:
                    logger.info("Index '%s' does not exist. Creating it...", index_uid)
                    await search_client.request(
                        "POST", 
                        "/indexes", 
                        json={"uid": index_uid, "primaryKey": "id"}
                    )
                    logger.info("Index '%s' created successfully.", index_uid)

                # 3. Update settings for filterable/sortable fields
                logger.info("Updating settings for index '%s'...", index_uid)
                settings_payload = {
                    "filterableAttributes": config["filterable"],
                    "sortableAttributes": config["sortable"]
                }
                await search_client.request(
                    "PATCH", 
                    f"/indexes/{index_uid}/settings", 
                    json=settings_payload
                )
                logger.info("Settings applied to '%s' (filterable: %s, sortable: %s).", 
                            index_uid, config["filterable"], config["sortable"])
                
            except Exception as e:
                logger.error("Failed to initialize index '%s': %s", index_uid, str(e))
                # Do not raise exception here, let initialization of other indexes continue.
