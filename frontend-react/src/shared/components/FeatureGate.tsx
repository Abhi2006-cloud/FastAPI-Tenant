import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Lock, Info, AlertCircle } from "lucide-react";
import * as Tooltip from "@radix-ui/react-tooltip";
import { useQuery } from "@tanstack/react-query";
import { apiClient, getActiveOrgId } from "../api/client.ts";
import type { EntitlementsResponse, FeatureState } from "../api/types.ts";
import { UpgradeDialog } from "./UpgradeDialog.tsx";

interface FeatureGateProps {
  feature: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const FeatureGate: React.FC<FeatureGateProps> = ({ feature, children, fallback }) => {
  const orgId = getActiveOrgId();
  const [dialogOpen, setDialogOpen] = useState(false);

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
    return <>{children}</>;
  }

  const featureDef = entitlements.features.find((f) => f.key === feature);
  const state: FeatureState = (featureDef?.state as FeatureState) || "included";

  // 1. Included: Normal rendering
  if (state === "included") {
    return <>{children}</>;
  }

  // 2. Plan Locked: Disabled control + Pro badge + tooltip + opens UpgradeDialog
  if (state === "plan_locked") {
    return (
      <>
        <Tooltip.Provider delayDuration={150}>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <div
                role="button"
                tabIndex={0}
                onClick={() => setDialogOpen(true)}
                onKeyDown={(e) => e.key === "Enter" && setDialogOpen(true)}
                className="inline-flex items-center gap-1.5 opacity-65 cursor-pointer select-none"
              >
                <div className="pointer-events-none">{children}</div>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[11px] font-semibold bg-[#F0FDFA] text-[#0F766E] border border-[#CCFBF1] rounded-[4px]">
                  <Lock className="w-2.5 h-2.5" />
                  Pro
                </span>
              </div>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                side="top"
                className="bg-[#18181B] text-white text-[12px] px-2.5 py-1.5 rounded-[4px] shadow max-w-[240px] z-50 text-center"
              >
                {featureDef?.description || "Upgrade required to access this feature. Click to request upgrade."}
                <Tooltip.Arrow className="fill-[#18181B]" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </Tooltip.Provider>

        <UpgradeDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          data={{
            code: "PLAN_FEATURE_LOCKED",
            feature,
            state: "plan_locked",
            required_plan: "pro",
            current_plan: entitlements.plan,
          }}
        />
      </>
    );
  }

  // 3. Deployment Disabled: "Not available on this deployment" badge + link to architecture doc page
  if (state === "deployment_disabled") {
    const docPath = feature === "email_delivery" ? "/docs/email" : "/docs/search";
    if (fallback) return <>{fallback}</>;
    return (
      <div className="p-3 bg-[#FAFAFA] border border-[#E4E4E7] rounded-[6px] flex items-center justify-between text-[13px]">
        <div className="flex items-center gap-2 text-[#71717A]">
          <Info className="w-4 h-4 text-[#A1A1AA]" />
          <span>Not available on this deployment</span>
        </div>
        <Link
          to={docPath}
          className="text-[#0F766E] hover:underline text-[12px] font-medium"
        >
          View architecture docs
        </Link>
      </div>
    );
  }

  // 4. Coming Soon: Badge, no CTA
  if (state === "coming_soon") {
    if (fallback) return <>{fallback}</>;
    return (
      <div className="inline-flex items-center gap-1.5 px-2 py-1 bg-[#F4F4F5] border border-[#E4E4E7] rounded-[4px] text-[12px] text-[#71717A]">
        <AlertCircle className="w-3.5 h-3.5 text-[#A1A1AA]" />
        <span>Coming soon</span>
      </div>
    );
  }

  return <>{children}</>;
};
