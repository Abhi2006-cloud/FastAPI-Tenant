import logging
from typing import Any, Dict, List, Optional
from app.infrastructure.search.client import search_client
from app.infrastructure.search.index_manager import IndexManager

logger = logging.getLogger(__name__)

class SearchRepository:
    """Performs direct operations on Meilisearch index documents using SearchClient."""
    
    def __init__(self) -> None:
        self.client = search_client

    def _get_full_index_name(self, base_name: str) -> str:
        return IndexManager.get_index_name(base_name)

    async def index_document(self, base_index: str, doc_id: str, document: Dict[str, Any]) -> None:
        """Add or update a document in the Meilisearch index."""
        index_uid = self._get_full_index_name(base_index)
        logger.info("Indexing document %s in %s", doc_id, index_uid)
        
        # Meilisearch expects documents as an array of JSON objects
        await self.client.request(
            "POST", 
            f"/indexes/{index_uid}/documents", 
            json=[document]
        )
        logger.info("Document %s indexed successfully in %s", doc_id, index_uid)

    async def delete_document(self, base_index: str, doc_id: str) -> None:
        """Delete a document from the Meilisearch index."""
        index_uid = self._get_full_index_name(base_index)
        logger.info("Deleting document %s from %s", doc_id, index_uid)
        
        await self.client.request(
            "DELETE", 
            f"/indexes/{index_uid}/documents/{doc_id}"
        )
        logger.info("Document %s deleted successfully from %s", doc_id, index_uid)

    async def search(
        self,
        base_index: str,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filter_str: Optional[str] = None,
        sort: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform search query on the given index."""
        index_uid = self._get_full_index_name(base_index)
        logger.info("Performing search query '%s' on %s with filter=%s, sort=%s", 
                    query, index_uid, filter_str, sort)
        
        payload: Dict[str, Any] = {
            "q": query,
            "limit": limit,
            "offset": offset,
            "attributesToHighlight": ["*"]
        }
        
        if filter_str:
            payload["filter"] = filter_str
            
        if sort:
            payload["sort"] = [sort]

        result = await self.client.request(
            "POST", 
            f"/indexes/{index_uid}/search", 
            json=payload
        )
        return result
