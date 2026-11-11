/**
 * Endpoints used by this page:
 * - GET /plans
 * - GET /organizations/{id}/entitlements
 * - POST /organizations/{id}/upgrade-request
 */
import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Sparkles } from "lucide-react";
import { apiClient } from "../../shared/api/client.ts";
import { useOrg } from "../../shared/context/OrgContext.tsx";
import type { PlanSchema } from "../../shared/api/types.ts";
import { UpgradeDialog } from "../../shared/components/UpgradeDialog.tsx";

export const BillingPage: React.FC = () => {
  const { entitlements } = useOrg();
  const [targetPlan, setTargetPlan] = useState<string | null>(null);

  // Fetch all plans from backend
  const { data: plans = [], isLoading } = useQuery<PlanSchema[]>({
    queryKey: ["plans"],
    queryFn: async () => {
      const res = await apiClient.get<PlanSchema[]>("/plans");
      return res.data;
    },
  });

  const currentPlanId = entitlements?.plan || "free";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Billing & Plans</h1>
        <p className="text-[13px] text-[#71717A] mt-0.5">
          Workspace capacity, limits, and plan tier comparisons. Upgrades are fulfilled by the platform administrator.
        </p>
      </div>

      {/* Plans Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {isLoading ? (
          [1, 2, 3].map((i) => (
            <div key={i} className="h-96 bg-white border border-[#E4E4E7] rounded-[6px] p-6 animate-pulse" />
          ))
        ) : (
          plans.map((p) => {
            const isCurrent = p.id === currentPlanId;

            return (
              <div
                key={p.id}
                className={`bg-white rounded-[6px] p-6 flex flex-col justify-between border ${
                  isCurrent ? "border-2 border-[#0F766E] shadow-sm" : "border-[#E4E4E7]"
                }`}
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-[16px] font-semibold text-[#18181B]">{p.name}</h2>
                    {isCurrent && (
                      <span className="px-2 py-0.5 text-[11px] font-medium tracking-wide uppercase bg-[#F0FDFA] text-[#0F766E] border border-[#CCFBF1] rounded-[4px]">
                        Current Plan
                      </span>
                    )}
                  </div>
                  <p className="text-[13px] text-[#52525B] leading-relaxed min-h-[40px]">
                    {p.description}
                  </p>

                  <div className="border-t border-[#E4E4E7] pt-4 space-y-2.5 text-[13px]">
                    <div className="flex items-center justify-between">
                      <span className="text-[#71717A]">Members</span>
                      <span className="font-medium text-[#18181B] tabular-nums">{p.limits.max_members}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#71717A]">Max Files</span>
                      <span className="font-medium text-[#18181B] tabular-nums">{p.limits.max_files}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#71717A]">Upload File Size</span>
                      <span className="font-medium text-[#18181B] tabular-nums">{p.limits.max_upload_mb} MB</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#71717A]">Database Storage</span>
                      <span className="font-medium text-[#18181B] tabular-nums">{p.limits.org_storage_mb} MB</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#71717A]">API Requests</span>
                      <span className="font-medium text-[#18181B] tabular-nums">{p.limits.api_requests_per_minute}/min</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#71717A]">Audit History</span>
                      <span className="font-medium text-[#18181B] tabular-nums">{p.limits.audit_history_days} days</span>
                    </div>
                  </div>

                  <div className="border-t border-[#E4E4E7] pt-4 space-y-2">
                    <span className="text-[11px] font-semibold text-[#71717A] uppercase tracking-wider block">
                      Features
                    </span>
                    {p.features.map((feat) => (
                      <div key={feat.key} className="flex items-center gap-2 text-[12px] text-[#52525B]">
                        <Check className="w-3.5 h-3.5 text-[#0F766E] shrink-0" />
                        <span>{feat.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-6">
                  {isCurrent ? (
                    <button
                      type="button"
                      disabled
                      className="w-full py-2 bg-[#F4F4F5] text-[#71717A] text-[13px] font-medium rounded-[6px] cursor-default"
                    >
                      Active on Workspace
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setTargetPlan(p.id)}
                      className="w-full py-2 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Request Upgrade</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Upgrade Dialog */}
      {targetPlan && (
        <UpgradeDialog
          open={!!targetPlan}
          onOpenChange={(open) => !open && setTargetPlan(null)}
          data={{
            code: "PLAN_FEATURE_LOCKED",
            required_plan: targetPlan,
            current_plan: currentPlanId,
          }}
        />
      )}
    </div>
  );
};
