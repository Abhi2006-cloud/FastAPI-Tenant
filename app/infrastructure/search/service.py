import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.cache import CacheService, CacheTTL
from app.core.database import async_session_factory
from app.infrastructure.search.client import search_client, MeilisearchUnavailableException
from app.infrastructure.search.repository import SearchRepository
from app.modules.search.models import SearchIndexFailure

logger = logging.getLogger(__name__)

class SearchService:
    """Unified entry point for search execution, caching, invalidation, and error logging."""
    
    def __init__(self) -> None:
        self.repo = SearchRepository()
        self.cache = CacheService()

    def _get_cache_key(
        self, 
        org_id: str, 
        index: str, 
        query: str, 
        limit: int, 
        offset: int, 
        sort: Optional[str]
    ) -> str:
        # Sanitize query to avoid newline issues in cache keys
        sanitized_query = query.replace("\n", " ").replace("\r", "")
        return f"search:{org_id}:{index}:{sanitized_query}:{limit}:{offset}:{sort or ''}"

    async def search(
        self,
        base_index: str,
        query: str,
        organization_id: UUID,
        limit: int = 10,
        offset: int = 0,
        sort: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform a tenant-isolated query on a specific index, using caching (Cache-Aside)."""
        if not search_client.enabled or not search_client.is_configured():
            raise MeilisearchUnavailableException("Search service is temporarily unavailable.")

        org_str = str(organization_id)
        
        # Enforce multi-tenancy filter
        if base_index == "organizations":
            filter_str = f"id = '{org_str}'"
        else:
            filter_str = f"organization_id = '{org_str}'"

        cache_key = self._get_cache_key(org_str, base_index, query, limit, offset, sort)
        
        # Cache check
        cached_res = await self.cache.get(cache_key)
        if cached_res is not None:
            try:
                return json.loads(cached_res)
            except Exception:
                pass

        # Query Meilisearch
        result = await self.repo.search(
            base_index=base_index,
            query=query,
            limit=limit,
            offset=offset,
            filter_str=filter_str,
            sort=sort
        )
        
        # Normalize totalHits for Meilisearch v1.1+ queries which return estimatedTotalHits
        if "totalHits" not in result and "estimatedTotalHits" in result:
            result["totalHits"] = result["estimatedTotalHits"]
        elif "totalHits" not in result:
            result["totalHits"] = 0


        # Cache the result (5 mins TTL)
        await self.cache.set(cache_key, result, ttl=CacheTTL.SHORT)
        
        # Log search query
        logger.info("Search query logged. Org: %s, Index: %s, Query: '%s'", org_str, base_index, query)
        
        return result

    async def global_search(
        self,
        query: str,
        organization_id: UUID,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Perform a tenant-isolated global search across files, members, and audit logs."""
        if not search_client.enabled or not search_client.is_configured():
            raise MeilisearchUnavailableException("Search service is temporarily unavailable.")

        org_str = str(organization_id)
        cache_key = self._get_cache_key(org_str, "global", query, limit, offset, None)

        cached_res = await self.cache.get(cache_key)
        if cached_res is not None:
            try:
                return json.loads(cached_res)
            except Exception:
                pass

        # Perform searches sequentially/concurrently
        files_res = await self.search("files", query, organization_id, limit, offset)
        members_res = await self.search("members", query, organization_id, limit, offset)
        audit_res = await self.search("audit_logs", query, organization_id, limit, offset)

        result = {
            "query": query,
            "organization_id": org_str,
            "files": files_res.get("hits", []),
            "members": members_res.get("hits", []),
            "audit_logs": audit_res.get("hits", []),
            "totals": {
                "files": files_res.get("totalHits", len(files_res.get("hits", []))),
                "members": members_res.get("totalHits", len(members_res.get("hits", []))),
                "audit_logs": audit_res.get("totalHits", len(audit_res.get("hits", [])))
            }
        }

        await self.cache.set(cache_key, result, ttl=CacheTTL.SHORT)
        return result

    async def index_document(self, base_index: str, doc_id: str, document: Dict[str, Any]) -> None:
        """Index document in Meilisearch and invalidate organization search cache."""
        await self.repo.index_document(base_index, doc_id, document)
        
        # Invalidate cache for this tenant
        org_id = doc_id if base_index == "organizations" else document.get("organization_id")
        if org_id:
            cache_pattern = f"search:{org_id}:*"
            await self.cache.invalidate_pattern(cache_pattern)
            logger.info("Cache invalidated for pattern: %s due to doc indexing", cache_pattern)

    async def delete_document(self, base_index: str, doc_id: str, organization_id: UUID) -> None:
        """Delete document from Meilisearch and invalidate organization search cache."""
        await self.repo.delete_document(base_index, doc_id)
        
        # Invalidate cache for this tenant
        org_id = str(organization_id)
        cache_pattern = f"search:{org_id}:*"
        await self.cache.invalidate_pattern(cache_pattern)
        logger.info("Cache invalidated for pattern: %s due to doc deletion", cache_pattern)

    async def record_indexing_failure(
        self,
        job_id: Optional[str],
        index_name: str,
        doc_id: str,
        operation: str,
        error_message: str,
        payload: Optional[Dict[str, Any]]
    ) -> None:
        """Log indexing failure details into the database search_index_failures table."""
        logger.warning(
            "Logging indexing failure to DB. Job: %s, Index: %s, Doc: %s, Error: %s",
            job_id, index_name, doc_id, error_message
        )
        async with async_session_factory() as session:
            try:
                failure = SearchIndexFailure(
                    job_id=job_id,
                    index_name=index_name,
                    document_id=doc_id,
                    operation=operation,
                    error_message=error_message[:1024],
                    payload=payload
                )
                session.add(failure)
                await session.commit()
                logger.info("Saved search index failure ID: %s to database", failure.id)
            except Exception as e:
                await session.rollback()
                logger.error("Failed to write search index failure record to DB: %s", str(e))
