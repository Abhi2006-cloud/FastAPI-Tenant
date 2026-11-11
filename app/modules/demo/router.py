"""
DEMO MODULE — router.py

Endpoints for automated sandbox/demo session creation and instant plan upgrade.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_organization_id_header
from app.core.rate_limit import rate_limit
from app.core.request_context import RequestInfo, get_request_info
from app.modules.auth.models import User
from app.modules.demo.schemas import DemoSessionResponse, DemoUpgradeResponse
from app.modules.demo.service import DemoService

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post(
    "/session",
    response_model=DemoSessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("demo_session", 10, 3600, key="ip"))],
)
async def create_demo_session(
    db: Annotated[AsyncSession, Depends(get_db)],
    request_info: Annotated[RequestInfo, Depends(get_request_info)],
) -> DemoSessionResponse:
    """Launch an ephemeral, fully populated demo workspace. Rate limited 10/hour/IP."""
    settings = get_settings()
    if not settings.demo_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo mode is disabled on this deployment",
        )

    return await DemoService(db).create_demo_session(
        ip_address=request_info.ip_address,
        user_agent=request_info.user_agent,
    )


@router.post("/upgrade", response_model=DemoUpgradeResponse)
async def upgrade_demo_workspace(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
) -> DemoUpgradeResponse:
    """Instantly toggle a demo workspace to the Pro plan to showcase locked vs unlocked features."""
    return await DemoService(db).upgrade_demo_organization(
        current_user=current_user,
        organization_id=organization_id,
    )

