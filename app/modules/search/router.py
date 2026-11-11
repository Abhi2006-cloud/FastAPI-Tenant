from typing import Annotated, Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_membership, get_current_user, get_organization_id_header
from app.core.exceptions import ForbiddenError
from app.core.rate_limit import rate_limit
from app.infrastructure.search.client import MeilisearchException, MeilisearchUnavailableException
from app.infrastructure.search.service import SearchService
from app.modules.auth.models import User
from app.modules.memberships.models import Membership
from app.modules.search.schemas import GlobalSearchResponse, SearchResponse
from app.modules.search.service import BasicSearchService

router = APIRouter(prefix="/search", tags=["search"])
search_service = SearchService()


@router.get(
    "/basic",
    response_model=GlobalSearchResponse,
    dependencies=[Depends(rate_limit("search_basic", 60, 60, key="org"))],
)
async def basic_search(
    db: Annotated[AsyncSession, Depends(get_db)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(get_current_membership)],
    q: str = Query(..., min_length=1, description="Search query string"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Any:
    """Basic SQL-backed case-insensitive search across files, members, and audit logs.

    Operates strictly within the tenant boundary and functions even when
    external search engines (Meilisearch) are disabled.
    """
    service = BasicSearchService(db)
    return await service.search_basic(
        organization_id=organization_id,
        query=q,
        limit=limit,
        offset=offset,
    )

def handle_search_exception(exc: Exception) -> None:
    """Standard handler to gracefully catch Meilisearch exceptions and return HTTP 503."""
    if isinstance(exc, (MeilisearchUnavailableException, MeilisearchException)):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is temporarily unavailable."
        )
    raise exc

@router.get("", response_model=GlobalSearchResponse)
async def global_search(
    q: str = Query("", description="Search query string"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    organization_id: Annotated[UUID, Depends(get_organization_id_header)] = None,
    _: Annotated[Membership, Depends(get_current_membership)] = None,
) -> Any:
    """Perform a global search across files, members, and audit logs inside the organization."""
    try:
        res = await search_service.global_search(
            query=q,
            organization_id=organization_id,
            limit=limit,
            offset=offset
        )
        return res
    except Exception as exc:
        handle_search_exception(exc)

@router.get("/organizations", response_model=SearchResponse)
async def search_organizations(
    q: str = Query("", description="Search query string"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: str | None = Query(None, description="Sorting parameter, e.g. created_at:desc"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    organization_id: Annotated[UUID, Depends(get_organization_id_header)] = None,
    _: Annotated[Membership, Depends(get_current_membership)] = None,
) -> Any:
    """Search organization details (returns current active organization if matching)."""
    try:
        res = await search_service.search(
            base_index="organizations",
            query=q,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            sort=sort
        )
        return res
    except Exception as exc:
        handle_search_exception(exc)

@router.get("/members", response_model=SearchResponse)
async def search_members(
    q: str = Query("", description="Search query string"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: str | None = Query(None, description="Sorting parameter, e.g. created_at:desc"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    organization_id: Annotated[UUID, Depends(get_organization_id_header)] = None,
    _: Annotated[Membership, Depends(get_current_membership)] = None,
) -> Any:
    """Search members of the organization by email, role, etc."""
    try:
        res = await search_service.search(
            base_index="members",
            query=q,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            sort=sort
        )
        return res
    except Exception as exc:
        handle_search_exception(exc)

@router.get("/files", response_model=SearchResponse)
async def search_files(
    q: str = Query("", description="Search query string"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: str | None = Query(None, description="Sorting parameter, e.g. created_at:desc"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    organization_id: Annotated[UUID, Depends(get_organization_id_header)] = None,
    _: Annotated[Membership, Depends(get_current_membership)] = None,
) -> Any:
    """Search files inside the organization by file name, file path, etc."""
    try:
        res = await search_service.search(
            base_index="files",
            query=q,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            sort=sort
        )
        return res
    except Exception as exc:
        handle_search_exception(exc)

@router.get("/audit_logs", response_model=SearchResponse)
async def search_audit_logs(
    q: str = Query("", description="Search query string"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: str | None = Query(None, description="Sorting parameter, e.g. created_at:desc"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    organization_id: Annotated[UUID, Depends(get_organization_id_header)] = None,
    _: Annotated[Membership, Depends(get_current_membership)] = None,
) -> Any:
    """Search audit logs inside the organization by action, resource type, metadata, etc."""
    try:
        res = await search_service.search(
            base_index="audit_logs",
            query=q,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            sort=sort
        )
        return res
    except Exception as exc:
        handle_search_exception(exc)
