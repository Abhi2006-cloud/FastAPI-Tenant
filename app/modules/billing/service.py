"""
BILLING MODULE — service.py

Core business logic for plans, entitlements, upgrade requests, and platform limits.
"""

from datetime import UTC, datetime
import time
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.redis import RedisClient
from app.modules.audit.events import (
    RESOURCE_BILLING,
    RESOURCE_ORGANIZATION,
    AuditAction,
)
from app.modules.audit.service import AuditLogService
from app.modules.billing.models import UpgradeRequest
from app.modules.billing.plans import (
    ALL_FEATURES,
    PLANS_CONFIG,
    PlanLimits,
    evaluate_feature_state,
    get_plan_limits,
)
from app.modules.billing.repository import UpgradeRequestRepository
from app.modules.billing.schemas import (
    EntitlementsResponse,
    FeatureItemSchema,
    PlanLimitsSchema,
    PlanSchema,
    PlatformLimitsResponse,
    UpgradeRequestCreate,
    UsageStats,
)
from app.modules.files.repository import FileRepository
from app.modules.memberships.repository import MembershipRepository
from app.modules.organizations.models import Organization
from app.modules.organizations.repository import OrganizationRepository


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UpgradeRequestRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.file_repo = FileRepository(db)
        self.membership_repo = MembershipRepository(db)

    async def get_plans(self) -> list[PlanSchema]:
        """Return all available plans, their configured quotas, and feature availability."""
        result: list[PlanSchema] = []
        for plan_key, plan_data in PLANS_CONFIG.items():
            limits: PlanLimits = plan_data["limits"]
            features_out: list[FeatureItemSchema] = []
            for f in ALL_FEATURES:
                state = evaluate_feature_state(f, plan_key)
                features_out.append(
                    FeatureItemSchema(
                        key=f.key,
                        label=f.label,
                        description=f.description,
                        min_plan=f.min_plan,
                        implemented=f.implemented,
                        state=state,
                    )
                )

            result.append(
                PlanSchema(
                    id=plan_data["id"],
                    name=plan_data["name"],
                    description=plan_data["description"],
                    limits=PlanLimitsSchema(
                        max_members=limits.max_members,
                        max_files=limits.max_files,
                        max_upload_mb=limits.max_upload_mb,
                        org_storage_mb=limits.org_storage_mb,
                        invites_per_hour=limits.invites_per_hour,
                        api_requests_per_minute=limits.api_requests_per_minute,
                        audit_history_days=limits.audit_history_days,
                    ),
                    features=features_out,
                )
            )
        return result

    async def get_entitlements(self, organization_id: UUID) -> EntitlementsResponse:
        """Compute real-time entitlement usage and quota boundaries for a tenant."""
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError("Organization not found")

        plan = org.plan or "free"
        limits = get_plan_limits(plan)

        # 1. Member usage
        members_count = await self.membership_repo.count_by_organization(organization_id)

        # 2. File & storage usage
        file_stats = await self.file_repo.get_statistics(organization_id)
        files_count = file_stats["total_files"]
        storage_bytes = file_stats["total_size_bytes"]
        storage_mb = round(storage_bytes / (1024 * 1024), 2)

        # 3. Invites rate limit tracking
        current_hour = int(time.time() // 3600)
        key = f"ratelimit:invite:{organization_id}:{current_hour}"
        invites_used = 0
        try:
            client = await RedisClient.get_client()
            raw_val = await client.get(key)
            if raw_val:
                invites_used = int(raw_val)
        except Exception:
            invites_used = 0

        invites_remaining = max(0, limits.invites_per_hour - invites_used)

        # 4. Feature states
        features_out = [
            FeatureItemSchema(
                key=f.key,
                label=f.label,
                description=f.description,
                min_plan=f.min_plan,
                implemented=f.implemented,
                state=evaluate_feature_state(f, plan),
            )
            for f in ALL_FEATURES
        ]

        return EntitlementsResponse(
            plan=plan,
            limits=PlanLimitsSchema(
                max_members=limits.max_members,
                max_files=limits.max_files,
                max_upload_mb=limits.max_upload_mb,
                org_storage_mb=limits.org_storage_mb,
                invites_per_hour=limits.invites_per_hour,
                api_requests_per_minute=limits.api_requests_per_minute,
                audit_history_days=limits.audit_history_days,
            ),
            usage=UsageStats(
                members_count=members_count,
                files_count=files_count,
                storage_bytes=storage_bytes,
                storage_mb=storage_mb,
                invites_used_this_hour=invites_used,
            ),
            features=features_out,
            invites_remaining_this_hour=invites_remaining,
        )

    async def create_upgrade_request(
        self,
        organization_id: UUID,
        requested_by: UUID,
        data: UpgradeRequestCreate,
    ) -> UpgradeRequest:
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError("Organization not found")

        req = await self.repo.create(
            organization_id=organization_id,
            requested_by=requested_by,
            requested_plan=data.requested_plan,
            message=data.message,
        )

        audit_service = AuditLogService(self.db)
        await audit_service.create_event(
            organization_id=organization_id,
            actor_user_id=requested_by,
            action=AuditAction.UPGRADE_REQUESTED,
            resource_type=RESOURCE_BILLING,
            resource_id=req.id,
            metadata={"requested_plan": data.requested_plan, "message": data.message},
        )
        return req

    async def list_upgrade_requests(self, status: str | None = None) -> list[UpgradeRequest]:
        return await self.repo.list_all(status=status)

    async def update_organization_plan(
        self,
        organization_id: UUID,
        new_plan: str,
        actor_user_id: UUID | None,
    ) -> Organization:
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError("Organization not found")

        normalized = new_plan.lower()
        if normalized not in PLANS_CONFIG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan: {new_plan}. Must be one of: {list(PLANS_CONFIG.keys())}",
            )

        old_plan = org.plan
        org.plan = normalized
        org.plan_updated_at = datetime.now(UTC)
        await self.org_repo.save(org)

        # Auto-approve matching pending upgrade requests for this org
        pending = await self.repo.list_by_organization(organization_id)
        for req in pending:
            if req.status == "pending" and req.requested_plan == normalized:
                await self.repo.update_status(req, "approved")

        audit_service = AuditLogService(self.db)
        await audit_service.create_event(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.PLAN_CHANGED,
            resource_type=RESOURCE_ORGANIZATION,
            resource_id=organization_id,
            metadata={"old_plan": old_plan, "new_plan": normalized},
        )
        return org

    @staticmethod
    def get_platform_limits() -> PlatformLimitsResponse:
        settings = get_settings()
        worker_mode = (
            "embedded"
            if settings.embedded_worker
            else ("sync" if settings.job_sync_mode else "external")
        )
        search_status = "enabled" if settings.is_search_enabled else "disabled"
        email_status = settings.effective_email_mode

        return PlatformLimitsResponse(
            deployment={
                "environment": settings.environment,
                "tier": "zero-cost-free-tier",
                "storage_backend": settings.storage_backend,
                "worker_mode": worker_mode,
            },
            compute_provider={
                "name": "Render Free Web Service",
                "memory_mb": 512,
                "cpu": "shared",
                "ephemeral_disk": True,
                "idle_sleep_minutes": 15,
                "cold_start_seconds": "30-60",
                "single_service": True,
            },
            database_provider={
                "name": "Neon Serverless Postgres",
                "storage_gb": 0.5,
                "pooled_connection": "-pooler" in (settings.database_url or ""),
                "auto_suspend": True,
            },
            redis_provider={
                "name": "Upstash Managed TLS Redis",
                "protocol": "rediss" if "rediss://" in (settings.redis_url or "") else "redis",
                "max_commands_per_second": 10000,
                "max_record_size_mb": 100,
                "max_data_size_mb": 250,
                "monthly_bandwidth_gb": 10,
            },
            services={
                "search": {
                    "provider": "Meilisearch Cloud",
                    "status": search_status,
                    "available": settings.is_search_enabled,
                },
                "email": {
                    "provider": settings.email_provider,
                    "mode": email_status,
                    "status": email_status,
                    "available": settings.is_production_email_enabled,
                },
            },
        )

