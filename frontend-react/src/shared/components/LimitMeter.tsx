import React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient, getActiveOrgId } from "../api/client.ts";
import type { EntitlementsResponse } from "../api/types.ts";

interface LimitMeterProps {
  metric: "members" | "files" | "storage" | "invites";
  label?: string;
  showBar?: boolean;
}

export const LimitMeter: React.FC<LimitMeterProps> = ({ metric, label, showBar = true }) => {
  const orgId = getActiveOrgId();

  const { data: entitlements, isLoading } = useQuery<EntitlementsResponse>({
    queryKey: ["entitlements", orgId],
    queryFn: async () => {
      if (!orgId) throw new Error("No active organization");
      const res = await apiClient.get<EntitlementsResponse>(`/organizations/${orgId}/entitlements`);
      return res.data;
    },
    enabled: !!orgId,
    staleTime: 30_000,
  });

  if (isLoading || !entitlements) {
    return <div className="h-4 w-24 bg-[#E4E4E7]/60 rounded animate-pulse" />;
  }

  let current = 0;
  let max = 0;
  let unit = "";
  let defaultLabel = "";

  switch (metric) {
    case "members":
      current = entitlements.usage.members_count;
      max = entitlements.limits.max_members;
      defaultLabel = "Members";
      break;
    case "files":
      current = entitlements.usage.files_count;
      max = entitlements.limits.max_files;
      defaultLabel = "Files";
      break;
    case "storage":
      current = entitlements.usage.storage_mb;
      max = entitlements.limits.org_storage_mb;
      unit = "MB";
      defaultLabel = "Storage";
      break;
    case "invites":
      current = entitlements.usage.invites_used_this_hour;
      max = entitlements.limits.invites_per_hour;
      defaultLabel = "Invites used this hour";
      break;
  }

  const percentage = max > 0 ? Math.min(100, Math.round((current / max) * 100)) : 0;
  const isNearLimit = percentage >= 80 && percentage < 100;
  const isAtLimit = percentage >= 100;

  let statusColor = "bg-[#0F766E]";
  if (isAtLimit) statusColor = "bg-[#DC2626]";
  else if (isNearLimit) statusColor = "bg-[#D97706]";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[12px]">
        <span className="text-[#71717A]">{label || defaultLabel}</span>
        <span className="font-medium text-[#18181B] tabular-nums">
          {current}
          {unit ? ` ${unit}` : ""} / {max}
          {unit ? ` ${unit}` : ""}
        </span>
      </div>
      {showBar && (
        <div className="w-full h-1.5 bg-[#E4E4E7] rounded-full overflow-hidden">
          <div
            className={`h-full ${statusColor} transition-all duration-300`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      )}
    </div>
  );
};
