"""
BILLING MODULE — schemas.py

Pydantic schemas for plans, entitlements, upgrade requests, and platform limits.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlanLimitsSchema(BaseModel):
    max_members: int
    max_files: int
    max_upload_mb: int
    org_storage_mb: int
    invites_per_hour: int
    api_requests_per_minute: int
    audit_history_days: int


class FeatureItemSchema(BaseModel):
    key: str
    label: str
    description: str
    min_plan: str
    implemented: bool
    state: str  # included | plan_locked | deployment_disabled | coming_soon


class PlanSchema(BaseModel):
    id: str
    name: str
    description: str
    limits: PlanLimitsSchema
    features: list[FeatureItemSchema]


class UsageStats(BaseModel):
    members_count: int
    files_count: int
    storage_bytes: int
    storage_mb: float
    invites_used_this_hour: int


class EntitlementsResponse(BaseModel):
    plan: str
    limits: PlanLimitsSchema
    usage: UsageStats
    features: list[FeatureItemSchema]
    invites_remaining_this_hour: int


class UpgradeRequestCreate(BaseModel):
    requested_plan: str = Field(..., pattern="^(pro|enterprise)$")
    message: str | None = None


class UpgradeRequestResponse(BaseModel):
    id: UUID
    organization_id: UUID
    requested_by: UUID | None
    requested_plan: str
    message: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminPlanUpdate(BaseModel):
    plan: str = Field(..., pattern="^(free|pro|enterprise)$")


class PlatformLimitsResponse(BaseModel):
    deployment: dict
    compute_provider: dict
    database_provider: dict
    redis_provider: dict
    services: dict

