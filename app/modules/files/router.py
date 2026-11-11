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
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_membership, get_current_user, get_organization_id_header
from app.core.rate_limit import rate_limit
from app.modules.auth.models import User
from app.modules.files.schemas import DeleteResponse, FileDetailResponse, FileResponse, FileStatisticsResponse
from app.modules.files.service import FileService
from app.modules.memberships.models import Membership

router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "/upload",
    response_model=FileResponse,
    status_code=201,
    dependencies=[Depends(rate_limit("file_upload", 60, 60, key="org"))],
)
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


@router.get("/stats", response_model=FileStatisticsResponse)
async def get_file_statistics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(get_current_membership)],
) -> FileStatisticsResponse:
    stats = await FileService(db).get_statistics(
        user_id=current_user.id,
        organization_id=organization_id,
    )
    return FileStatisticsResponse(**stats)


@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file(
    file_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(get_current_membership)],
) -> FileDetailResponse:
    file_record = await FileService(db).get_file(
        user_id=current_user.id,
        organization_id=organization_id,
        file_id=file_id,
    )
    
    return FileDetailResponse(
        id=file_record.id,
        organization_id=file_record.organization_id,
        uploaded_by=file_record.uploaded_by,
        file_name=file_record.file_name,
        file_path=file_record.file_path,
        file_size=file_record.file_size,
        created_at=file_record.created_at,
        download_url=f"/files/{file_id}/download",
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(get_current_membership)],
):
    content, filename = await FileService(db).download_file(
        user_id=current_user.id,
        organization_id=organization_id,
        file_id=file_id,
    )
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/{file_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_file(
    file_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id_header)],
    _: Annotated[Membership, Depends(get_current_membership)],
) -> DeleteResponse:
    await FileService(db).delete_file(
        user_id=current_user.id,
        organization_id=organization_id,
        file_id=file_id,
    )
    return DeleteResponse()
