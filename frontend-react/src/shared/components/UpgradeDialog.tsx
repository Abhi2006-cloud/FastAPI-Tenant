import React, { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Sparkles } from "lucide-react";
import { apiClient, getActiveOrgId } from "../api/client.ts";
import type { PlanUpgradeErrorData } from "../api/types.ts";

interface UpgradeDialogProps {
  data: PlanUpgradeErrorData | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const UpgradeDialog: React.FC<UpgradeDialogProps> = ({ data, open, onOpenChange }) => {
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!data) return null;

  const targetPlan = data.required_plan || "pro";
  const orgId = getActiveOrgId();

  const handleRequestUpgrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgId) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await apiClient.post(`/organizations/${orgId}/upgrade-request`, {
        requested_plan: targetPlan,
        message: message.trim() || undefined,
      });
      setSuccess(true);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setErrorMsg(axiosErr.response?.data?.detail || "Failed to submit upgrade request.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setSuccess(false);
    setErrorMsg(null);
    setMessage("");
    onOpenChange(false);
  };

  return (
    <Dialog.Root open={open} onOpenChange={handleClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50 backdrop-blur-[1px]" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-[6px] border border-[#E4E4E7] p-6 w-full max-w-[480px] shadow-lg z-50 focus:outline-none">
          <div className="flex items-center justify-between pb-3 border-b border-[#E4E4E7]">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#0F766E]" />
              <Dialog.Title className="text-[15px] font-semibold text-[#18181B]">
                {data.code === "PLAN_LIMIT_REACHED" ? "Plan Limit Reached" : "Upgrade Required"}
              </Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="text-[#71717A] hover:text-[#18181B] p-1 rounded hover:bg-[#FAFAFA]"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="py-4">
            {success ? (
              <div className="space-y-4">
                <div className="p-3 bg-[#F0FDF4] border border-[#DCFCE7] rounded-[6px] text-[13px] text-[#166534]">
                  Upgrade request submitted. A platform administrator will review and process your workspace plan change.
                </div>
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={handleClose}
                    className="px-4 py-2 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px]"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleRequestUpgrade} className="space-y-4">
                <Dialog.Description className="text-[13px] text-[#52525B]">
                  {data.code === "PLAN_LIMIT_REACHED" ? (
                    <>
                      Your workspace has reached the limit for{" "}
                      <span className="font-semibold text-[#18181B]">{data.limit || "resource"}</span>{" "}
                      ({data.current} of {data.max}) on the {data.plan || "current"} plan.
                    </>
                  ) : (
                    <>
                      The feature <span className="font-semibold text-[#18181B]">{data.feature}</span> is
                      locked on the {data.current_plan || "free"} plan and requires the{" "}
                      <span className="capitalize font-semibold text-[#0F766E]">{targetPlan}</span> tier.
                    </>
                  )}
                </Dialog.Description>

                {errorMsg && (
                  <div className="p-2.5 bg-[#FEF2F2] border border-[#FEE2E2] rounded-[6px] text-[12px] text-[#DC2626]">
                    {errorMsg}
                  </div>
                )}

                <div>
                  <label htmlFor="upgrade-message" className="block text-[12px] font-medium text-[#71717A] mb-1">
                    Message for Administrator (Optional)
                  </label>
                  <textarea
                    id="upgrade-message"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Describe your team size, storage requirements, or use case..."
                    rows={3}
                    className="w-full text-[13px] p-2.5 border border-[#E4E4E7] rounded-[6px] focus:outline-none focus:ring-1 focus:ring-[#0F766E] resize-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={handleClose}
                    className="px-3 py-1.5 border border-[#E4E4E7] text-[13px] text-[#52525B] hover:bg-[#FAFAFA] rounded-[6px]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-1.5 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] disabled:opacity-50"
                  >
                    {submitting ? "Submitting..." : `Request ${targetPlan.toUpperCase()} Upgrade`}
                  </button>
                </div>
              </form>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

