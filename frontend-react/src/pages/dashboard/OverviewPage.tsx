/**
 * Endpoints used by this page:
 * - GET /organizations/{id}/entitlements
 * - GET /audit-logs
 * - GET /organizations/{id}
 */
import React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Shield, Users, FileText, HardDrive, Mail, Server } from "lucide-react";
import { apiClient, getActiveOrgId } from "../../shared/api/client.ts";
import { useOrg } from "../../shared/context/OrgContext.tsx";
import type { AuditLogListResponse } from "../../shared/api/types.ts";
import { LimitMeter } from "../../shared/components/LimitMeter.tsx";

export const OverviewPage: React.FC = () => {
  const orgId = getActiveOrgId();
  const { activeOrg, entitlements, isLoading } = useOrg();

  // Recent 5 audit logs
  const { data: auditData } = useQuery<AuditLogListResponse>({
    queryKey: ["audit-logs", orgId, "recent"],
    queryFn: async () => {
      if (!orgId) throw new Error("No active org");
      const res = await apiClient.get<AuditLogListResponse>("/audit-logs", {
        params: { page: 1, page_size: 5 },
      });
      return res.data;
    },
    enabled: !!orgId,
  });

  if (isLoading || !entitlements) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-[#E4E4E7]/60 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-white border border-[#E4E4E7] rounded-[6px] p-4 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const { usage, limits, plan } = entitlements;

  return (
    <div className="space-y-6">
      {/* Title & Plan Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">
            {activeOrg?.name} Overview
          </h1>
          <p className="text-[13px] text-[#71717A] mt-0.5">
            Real-time multi-tenant quotas, entitlements, and recent audit activity.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to={`/o/${orgId}/billing`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium border border-[#E4E4E7] rounded-[6px] hover:bg-[#F4F4F5] transition-colors"
          >
            <span>Manage Plan</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-[#71717A]" />
          </Link>
        </div>
      </div>

      {/* Usage Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Members Quota */}
        <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-4 space-y-2">
          <div className="flex items-center justify-between text-[#71717A]">
            <span className="text-[12px] font-medium">Workspace Members</span>
            <Users className="w-4 h-4 text-[#A1A1AA]" />
          </div>
          <div className="text-[20px] font-semibold text-[#18181B] tabular-nums">
            {usage.members_count} <span className="text-[13px] font-normal text-[#71717A]">/ {limits.max_members}</span>
          </div>
          <LimitMeter metric="members" showBar={true} />
        </div>

        {/* Files Quota */}
        <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-4 space-y-2">
          <div className="flex items-center justify-between text-[#71717A]">
            <span className="text-[12px] font-medium">Total Files</span>
            <FileText className="w-4 h-4 text-[#A1A1AA]" />
          </div>
          <div className="text-[20px] font-semibold text-[#18181B] tabular-nums">
            {usage.files_count} <span className="text-[13px] font-normal text-[#71717A]">/ {limits.max_files}</span>
          </div>
          <LimitMeter metric="files" showBar={true} />
        </div>

        {/* Storage Quota */}
        <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-4 space-y-2">
          <div className="flex items-center justify-between text-[#71717A]">
            <span className="text-[12px] font-medium">Database Storage</span>
            <HardDrive className="w-4 h-4 text-[#A1A1AA]" />
          </div>
          <div className="text-[20px] font-semibold text-[#18181B] tabular-nums">
            {usage.storage_mb} MB{" "}
            <span className="text-[13px] font-normal text-[#71717A]">/ {limits.org_storage_mb} MB</span>
          </div>
          <LimitMeter metric="storage" showBar={true} />
        </div>

        {/* Invites Rate Quota */}
        <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-4 space-y-2">
          <div className="flex items-center justify-between text-[#71717A]">
            <span className="text-[12px] font-medium">Hourly Invites</span>
            <Mail className="w-4 h-4 text-[#A1A1AA]" />
          </div>
          <div className="text-[20px] font-semibold text-[#18181B] tabular-nums">
            {entitlements.invites_remaining_this_hour}{" "}
            <span className="text-[13px] font-normal text-[#71717A]">left this hour</span>
          </div>
          <LimitMeter metric="invites" showBar={true} />
        </div>
      </div>

      {/* Plan Card & Free Infrastructure Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Plan Summary Card */}
        <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-semibold text-[#18181B]">Current Plan</span>
            <span className="px-2 py-0.5 text-[11px] font-medium tracking-wide uppercase bg-[#F0FDFA] text-[#0F766E] border border-[#CCFBF1] rounded-[4px]">
              {plan}
            </span>
          </div>
          <p className="text-[12px] text-[#71717A] leading-relaxed">
            API rate limit: {limits.api_requests_per_minute} req/min. Audit log retention: {limits.audit_history_days} days. Maximum single upload size: {limits.max_upload_mb} MB.
          </p>
          <div className="pt-1">
            <Link
              to={`/o/${orgId}/billing`}
              className="text-[12px] text-[#0F766E] hover:underline font-medium"
            >
              Compare tiers & request upgrade →
            </Link>
          </div>
        </div>

        {/* Free Infrastructure Strip linking to /platform */}
        <div className="md:col-span-2 bg-[#FAFAFA] border border-[#E4E4E7] rounded-[6px] p-5 flex flex-col justify-between">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-[13px] font-semibold text-[#18181B]">
              <Server className="w-4 h-4 text-[#0F766E]" />
              <span>Zero-Cost Infrastructure Stack</span>
            </div>
            <p className="text-[12px] text-[#52525B] leading-relaxed">
              This deployment runs on Render Free (ephemeral web service), Neon Serverless PostgreSQL (cold-start pooler), and Upstash Redis. File blobs persist inside PostgreSQL without external paid object storage.
            </p>
          </div>
          <div className="pt-3">
            <Link
              to="/platform"
              className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#0F766E] hover:underline"
            >
              <span>Inspect live infrastructure limits & queue health</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Recent 5 Audit Events */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] overflow-hidden">
        <div className="px-4 py-3 border-b border-[#E4E4E7] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#71717A]" />
            <h2 className="text-[13px] font-semibold text-[#18181B]">Recent Audit Events</h2>
          </div>
          <Link
            to={`/o/${orgId}/audit`}
            className="text-[12px] text-[#0F766E] hover:underline font-medium"
          >
            View all logs →
          </Link>
        </div>

        <div className="divide-y divide-[#E4E4E7]">
          {auditData?.items && auditData.items.length > 0 ? (
            auditData.items.map((event) => (
              <div key={event.id} className="px-4 py-2.5 flex items-center justify-between text-[13px]">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-[11px] font-medium bg-[#F4F4F5] text-[#52525B] px-1.5 py-0.5 rounded">
                    {event.action}
                  </span>
                  <span className="text-[#52525B] text-[12px] capitalize">
                    {event.resource_type}
                  </span>
                </div>
                <div className="text-[12px] text-[#71717A] tabular-nums">
                  {event.created_at ? new Date(event.created_at).toLocaleString() : "—"}
                </div>
              </div>
            ))
          ) : (
            <div className="p-6 text-center text-[13px] text-[#71717A]">
              No audit events recorded yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
