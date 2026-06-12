"""
FILES MODULE — router.py

Tenant-scoped file API. Requires BOTH:
  - Authorization: Bearer <jwt>
  - X-Organization-Id: <org uuid from POST /organizations or GET /organizations/my>

Depends chain on each route:
  get_current_user -> get_organization_id_header -> get_current_membership
Then service runs upload/list for that organization_id only.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_membership, get_current_user, get_organization_id_header
from app.modules.auth.models import User
from app.modules.files.schemas import FileResponse
from app.modules.files.service import FileService
from app.modules.memberships.models import Membership

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileResponse, status_code=201)
async def upload_file(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(get_current_membership)],
    file: UploadFile = File(...),
) -> FileResponse:
    record = await FileService(db).upload_file(
        user_id=current_user.id,
        organization_id=organization_id,
        upload=file,
    )
    return FileResponse.model_validate(record)


@router.get("", response_model=list[FileResponse])
async def list_files(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(get_current_membership)],
) -> list[FileResponse]:
    records = await FileService(db).list_files(
        user_id=current_user.id,
        organization_id=organization_id,
    )
    return [FileResponse.model_validate(record) for record in records]
