from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class SearchHit(BaseModel):
    id: str
    organization_id: Optional[str] = None
    created_at: Optional[int] = None
    # Flexible field container for index specific fields
    fields: Dict[str, Any] = Field(default_factory=dict)
    # Formatted highlights container from Meilisearch (_formatted)
    formatted: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    hits: List[Dict[str, Any]]
    query: str
    processing_time_ms: int = Field(alias="processingTimeMs")
    limit: int
    offset: int
    total_hits: int = Field(alias="totalHits")

class GlobalSearchResponse(BaseModel):
    query: str
    organization_id: str
    files: List[Dict[str, Any]]
    members: List[Dict[str, Any]]
    audit_logs: List[Dict[str, Any]]
    totals: Dict[str, int]
