import type { components, paths } from "./schema.d.ts";

export type Schemas = components["schemas"];

export type UserResponse = Schemas["UserResponse"];
export type TokenResponse = Schemas["TokenResponse"];
export type OrganizationResponse = Schemas["OrganizationResponse"];
export type EntitlementsResponse = Schemas["EntitlementsResponse"];
export type PlanSchema = Schemas["PlanSchema"];
export type PlatformLimitsResponse = Schemas["PlatformLimitsResponse"];
export type UpgradeRequestResponse = Schemas["UpgradeRequestResponse"];
export type InvitationResponse = Schemas["InvitationResponse"];
export type MemberListResponse = Schemas["MemberListResponse"];
export type FileResponse = Schemas["FileResponse"];
export type FileStatisticsResponse = Schemas["FileStatisticsResponse"];
export type AuditLogResponse = Schemas["AuditLogResponse"];
export type AuditLogListResponse = Schemas["AuditLogListResponse"];
export type SessionResponse = Schemas["SessionResponse"];
export type SessionListResponse = Schemas["SessionListResponse"];
export type GlobalSearchResponse = Schemas["GlobalSearchResponse"];
export type EmailLogResponse = Schemas["EmailLogResponse"];
export type EmailLogListResponse = Schemas["EmailLogListResponse"];
export type EmailStatsResponse = Schemas["EmailStatsResponse"];
export type DemoSessionResponse = Schemas["DemoSessionResponse"];
export type DemoUpgradeResponse = Schemas["DemoUpgradeResponse"];

export type FeatureState = "included" | "plan_locked" | "deployment_disabled" | "coming_soon";

export interface PlanUpgradeErrorData {
  code: "PLAN_FEATURE_LOCKED" | "PLAN_LIMIT_REACHED";
  feature?: string;
  limit?: string;
  state?: FeatureState;
  required_plan?: string;
  current_plan?: string;
  current?: number;
  max?: number;
  plan?: string;
}

export type { paths };
