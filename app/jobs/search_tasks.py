import logging
from uuid import UUID
from rq import get_current_job

from app.core.database import worker_session_factory as async_session_factory
from app.jobs.async_runner import run_async
from app.infrastructure.search.service import SearchService
from app.infrastructure.search.document_mapper import (
    map_organization,
    map_member,
    map_file,
    map_audit_log
)
from app.modules.auth.models import User  # noqa: F401
from app.modules.organizations.models import Organization
from app.modules.memberships.models import Membership
from app.modules.files.models import FileRecord
from app.modules.audit.models import AuditLog
from app.modules.invitations.models import Invitation  # noqa: F401
from app.modules.search.models import SearchIndexFailure  # noqa: F401
from sqlalchemy import select
from sqlalchemy.orm import selectinload



logger = logging.getLogger(__name__)
search_service = SearchService()

def handle_job_failure(exc: Exception, index_name: str, doc_id: str, operation: str, payload: dict = None):
    """Inspects the active RQ job to determine if retries are exhausted.
    
    If yes, stores the failure info in the database and logs a final failure.
    If no, raises the exception to trigger the retry mechanism.
    """
    job = get_current_job()
    if not job:
        logger.warning("Sync mode search indexing failure for index=%s, doc_id=%s: %s", index_name, doc_id, str(exc))
        return

    job_id = job.id
    is_final = True
    retries_left = getattr(job, "retries_left", 0) or 0
    if retries_left > 0:
        is_final = False


    if is_final:
        logger.error("Job %s final indexing failure for index=%s, doc_id=%s: %s", 
                     job_id, index_name, doc_id, str(exc))
        try:
            # Save failure record in database
            run_async(
                search_service.record_indexing_failure(
                    job_id=job_id,
                    index_name=index_name,
                    doc_id=doc_id,
                    operation=operation,
                    error_message=str(exc),
                    payload=payload
                )
            )
        except Exception as save_err:
            logger.error("Failed to save final indexing failure for doc %s: %s", doc_id, str(save_err))
    else:
        logger.warning("Job %s indexing attempt failed for index=%s, doc_id=%s (retries left=%s). Retrying...",
                       job_id, index_name, doc_id, job.retries_left)
        raise exc

# Organization Tasks
async def _index_organization(org_id: str) -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(Organization).where(Organization.id == UUID(org_id)))
        org = result.scalar_one_or_none()
        if not org:
            logger.warning("Organization %s not found for search indexing.", org_id)
            return
        doc = map_organization(org)
        await search_service.index_document("organizations", org_id, doc)

def index_organization_task(org_id: str) -> None:
    logger.info("Background job: index_organization org_id=%s", org_id)
    try:
        run_async(_index_organization(org_id))
    except Exception as exc:
        handle_job_failure(exc, "organizations", org_id, "index", {"org_id": org_id})

def delete_organization_task(org_id: str) -> None:
    logger.info("Background job: delete_organization org_id=%s", org_id)
    try:
        run_async(search_service.delete_document("organizations", org_id, UUID(org_id)))
    except Exception as exc:
        handle_job_failure(exc, "organizations", org_id, "delete", {"org_id": org_id})

# Member Tasks
async def _index_member(membership_id: str) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Membership)
            .options(selectinload(Membership.user))
            .where(Membership.id == UUID(membership_id))
        )
        membership = result.scalar_one_or_none()
        if not membership:
            logger.warning("Membership %s not found for search indexing.", membership_id)
            return
        doc = map_member(membership)
        await search_service.index_document("members", membership_id, doc)

def index_member_task(membership_id: str) -> None:
    logger.info("Background job: index_member membership_id=%s", membership_id)
    try:
        run_async(_index_member(membership_id))
    except Exception as exc:
        handle_job_failure(exc, "members", membership_id, "index", {"membership_id": membership_id})

def delete_member_task(membership_id: str, organization_id: str) -> None:
    logger.info("Background job: delete_member membership_id=%s", membership_id)
    try:
        run_async(search_service.delete_document("members", membership_id, UUID(organization_id)))
    except Exception as exc:
        handle_job_failure(exc, "members", membership_id, "delete", {
            "membership_id": membership_id, 
            "organization_id": organization_id
        })

# File Tasks
async def _index_file(file_id: str) -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(FileRecord).where(FileRecord.id == UUID(file_id)))
        file_rec = result.scalar_one_or_none()
        if not file_rec:
            logger.warning("FileRecord %s not found for search indexing.", file_id)
            return
        doc = map_file(file_rec)
        await search_service.index_document("files", file_id, doc)

def index_file_task(file_id: str) -> None:
    logger.info("Background job: index_file file_id=%s", file_id)
    try:
        run_async(_index_file(file_id))
    except Exception as exc:
        handle_job_failure(exc, "files", file_id, "index", {"file_id": file_id})

def delete_file_task(file_id: str, organization_id: str) -> None:
    logger.info("Background job: delete_file file_id=%s", file_id)
    try:
        run_async(search_service.delete_document("files", file_id, UUID(organization_id)))
    except Exception as exc:
        handle_job_failure(exc, "files", file_id, "delete", {
            "file_id": file_id, 
            "organization_id": organization_id
        })

# Audit Log Tasks
async def _index_audit_log(audit_log_id: str) -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(AuditLog).where(AuditLog.id == UUID(audit_log_id)))
        audit_log = result.scalar_one_or_none()
        if not audit_log:
            logger.warning("AuditLog %s not found for search indexing.", audit_log_id)
            return
        doc = map_audit_log(audit_log)
        await search_service.index_document("audit_logs", audit_log_id, doc)

def index_audit_log_task(audit_log_id: str) -> None:
    logger.info("Background job: index_audit_log audit_log_id=%s", audit_log_id)
    try:
        run_async(_index_audit_log(audit_log_id))
    except Exception as exc:
        handle_job_failure(exc, "audit_logs", audit_log_id, "index", {"audit_log_id": audit_log_id})
