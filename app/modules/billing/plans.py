"""
BILLING MODULE — plans.py

Single source of truth for plan tiers, limits, and feature entitlements.
"""

from dataclasses import dataclass
from typing import Literal

from app.core.config import get_settings

PlanType = Literal["free", "pro", "enterprise"]
FeatureState = Literal["included", "plan_locked", "deployment_disabled", "coming_soon"]

PLAN_ORDER: dict[str, int] = {
    "free": 0,
    "pro": 1,
    "enterprise": 2,
}


@dataclass(frozen=True)
class PlanLimits:
    max_members: int
    max_files: int
    max_upload_mb: int
    org_storage_mb: int
    invites_per_hour: int
    api_requests_per_minute: int
    audit_history_days: int

    @property
    def org_storage_bytes(self) -> int:
        return self.org_storage_mb * 1024 * 1024

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@dataclass(frozen=True)
class FeatureDefinition:
    key: str
    label: str
    description: str
    min_plan: str
    implemented: bool


PLANS_CONFIG: dict[str, dict] = {
    "free": {
        "id": "free",
        "name": "Free",
        "description": "Essential multi-tenant workspace for small teams evaluating the platform.",
        "limits": PlanLimits(
            max_members=5,
            max_files=20,
            max_upload_mb=2,
            org_storage_mb=25,
            invites_per_hour=5,
            api_requests_per_minute=60,
            audit_history_days=7,
        ),
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "description": "Expanded capacity, extended audit history, and team collaboration features.",
        "limits": PlanLimits(
            max_members=50,
            max_files=500,
            max_upload_mb=10,
            org_storage_mb=200,
            invites_per_hour=20,
            api_requests_per_minute=300,
            audit_history_days=365,
        ),
    },
    "enterprise": {
        "id": "enterprise",
        "name": "Enterprise",
        "description": "High-volume quotas, dedicated rate limits, and custom workspace management.",
        "limits": PlanLimits(
            max_members=500,
            max_files=5000,
            max_upload_mb=50,
            org_storage_mb=2000,
            invites_per_hour=100,
            api_requests_per_minute=1000,
            audit_history_days=730,
        ),
    },
}

ALL_FEATURES: list[FeatureDefinition] = [
    FeatureDefinition(
        key="audit_export",
        label="Audit Log Export",
        description="Stream and export compliance audit logs as CSV.",
        min_plan="pro",
        implemented=True,
    ),
    FeatureDefinition(
        key="advanced_audit_filters",
        label="Advanced Audit Filters",
        description="Extended filtering and search across historical audit events.",
        min_plan="pro",
        implemented=True,
    ),
    FeatureDefinition(
        key="email_delivery",
        label="Automated Email Delivery",
        description="Transactional invite and notification delivery via email provider.",
        min_plan="pro",
        implemented=True,
    ),
    FeatureDefinition(
        key="meilisearch_search",
        label="Full-Text Search",
        description="Fast indexed full-text search across tenant resources.",
        min_plan="pro",
        implemented=True,
    ),
    FeatureDefinition(
        key="realtime_notifications",
        label="Real-time Notifications",
        description="Instant WebSocket-driven notifications for team activities.",
        min_plan="pro",
        implemented=False,
    ),
    FeatureDefinition(
        key="sso",
        label="Single Sign-On (SSO / SAML)",
        description="Enterprise identity provider integration and SAML/OIDC SSO.",
        min_plan="enterprise",
        implemented=False,
    ),
    FeatureDefinition(
        key="api_keys",
        label="API Keys & Webhooks",
        description="Programmatic workspace access and developer webhooks.",
        min_plan="pro",
        implemented=False,
    ),
]


def get_plan_limits(plan: str) -> PlanLimits:
    normalized = plan.lower() if plan else "free"
    plan_data = PLANS_CONFIG.get(normalized, PLANS_CONFIG["free"])
    return plan_data["limits"]


def evaluate_feature_state(feature: FeatureDefinition, current_plan: str) -> FeatureState:
    settings = get_settings()
    if not feature.implemented:
        return "coming_soon"

    curr_tier = PLAN_ORDER.get(current_plan.lower(), 0)
    required_tier = PLAN_ORDER.get(feature.min_plan.lower(), 0)

    if curr_tier < required_tier:
        return "plan_locked"

    # Plan includes the feature. Verify deployment capabilities
    if feature.key == "email_delivery" and not settings.is_production_email_enabled:
        return "deployment_disabled"
    if feature.key == "meilisearch_search" and not settings.is_search_enabled:
        return "deployment_disabled"

    return "included"

