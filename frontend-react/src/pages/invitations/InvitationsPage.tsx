/**
 * Endpoints used by this page:
 * - GET /organizations/{id}/invitations
 * - POST /organizations/{id}/invite
 * - POST /invitations/{id}/resend
 * - DELETE /organizations/{id}/invitations/{id}
 */
import React, { useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { useQuery } from "@tanstack/react-query";
import { UserPlus, Copy, Check, RotateCw, XCircle, Info } from "lucide-react";
import { apiClient, getActiveOrgId } from "../../shared/api/client.ts";
import { useOrg } from "../../shared/context/OrgContext.tsx";
import type { InvitationResponse } from "../../shared/api/types.ts";
import { LimitMeter } from "../../shared/components/LimitMeter.tsx";
import { useToast } from "../../shared/components/Toast.tsx";

export const InvitationsPage: React.FC = () => {
  const orgId = getActiveOrgId();
  const { role: myRole } = useOrg();
  const { showToast } = useToast();

  const isOwnerOrAdmin = myRole === "owner" || myRole === "admin";

  const [emailInput, setEmailInput] = useState("");
  const [inviting, setInviting] = useState(false);
  const [createdInvite, setCreatedInvite] = useState<InvitationResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState("pending");

  // Fetch invitations for organization
  const { data: invitations = [], isLoading, refetch } = useQuery<InvitationResponse[]>({
    queryKey: ["invitations", orgId, activeTab],
    queryFn: async () => {
      if (!orgId) throw new Error("No active org");
      const res = await apiClient.get<InvitationResponse[]>(`/organizations/${orgId}/invitations`, {
        params: { status: activeTab },
      });
      return res.data;
    },
    enabled: !!orgId && isOwnerOrAdmin,
  });

  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailInput.trim() || !orgId) return;
    setInviting(true);
    setCreatedInvite(null);
    try {
      const res = await apiClient.post<InvitationResponse>(`/organizations/${orgId}/invite`, {
        email: emailInput.trim(),
      });
      setCreatedInvite(res.data);
      setEmailInput("");
      showToast("Invitation created.", "success");
      refetch();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: { code?: string; limit?: string } } } };
      // 402/429 handled automatically by client interceptor
      if (axiosErr.response?.data?.detail && typeof axiosErr.response.data.detail === "string") {
        showToast(axiosErr.response.data.detail, "error");
      }
    } finally {
      setInviting(false);
    }
  };

  const handleRevoke = async (invitationId: string) => {
    if (!orgId) return;
    try {
      await apiClient.delete(`/organizations/${orgId}/invitations/${invitationId}`);
      showToast("Invitation revoked.", "success");
      refetch();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      showToast(axiosErr.response?.data?.detail || "Failed to revoke invitation.", "error");
    }
  };

  const handleResend = async (invitationId: string) => {
    try {
      await apiClient.post(`/invitations/${invitationId}/resend`);
      showToast("Invitation resent.", "success");
      refetch();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      showToast(axiosErr.response?.data?.detail || "Failed to resend invitation.", "error");
    }
  };

  const copyToClipboard = (url: string) => {
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!isOwnerOrAdmin) {
    return (
      <div className="p-8 bg-white border border-[#E4E4E7] rounded-[6px] text-center space-y-2">
        <h2 className="text-[15px] font-semibold text-[#18181B]">Access Restricted</h2>
        <p className="text-[13px] text-[#71717A]">
          Only workspace owners and administrators can create and manage invitations.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Invitations</h1>
        <p className="text-[13px] text-[#71717A] mt-0.5">
          Invite teammates into this tenant workspace.
        </p>
      </div>

      {/* Invite Creation Card */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between pb-2 border-b border-[#E4E4E7]">
          <div className="flex items-center gap-2">
            <UserPlus className="w-4 h-4 text-[#0F766E]" />
            <h2 className="text-[14px] font-semibold text-[#18181B]">Invite Teammate</h2>
          </div>
          <div className="flex items-center gap-6">
            <div className="w-36">
              <LimitMeter metric="members" />
            </div>
            <div className="w-36">
              <LimitMeter metric="invites" />
            </div>
          </div>
        </div>

        <form onSubmit={handleCreateInvite} className="flex gap-2">
          <input
            type="email"
            required
            value={emailInput}
            onChange={(e) => setEmailInput(e.target.value)}
            placeholder="colleague@example.com"
            className="flex-1 text-[13px] px-3 py-1.5 border border-[#E4E4E7] rounded-[6px] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
          />
          <button
            type="submit"
            disabled={inviting || !emailInput.trim()}
            className="px-4 py-1.5 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] disabled:opacity-50 transition-colors"
          >
            {inviting ? "Sending..." : "Send Invite"}
          </button>
        </form>

        {/* Manual Delivery Callout (Development Token Experience) */}
        {createdInvite && (
          <div className="p-4 bg-[#F0FDFA] border border-[#CCFBF1] rounded-[6px] space-y-2">
            <div className="flex items-center gap-2 text-[13px] font-medium text-[#0F766E]">
              <Info className="w-4 h-4 shrink-0" />
              <span>Invitation Link Ready</span>
            </div>
            {createdInvite.delivery_mode === "manual" && (
              <p className="text-[12px] text-[#115E59]">
                Email delivery is a Pro feature and is not enabled on this deployment. Share this link with the invitee. Email delivery for Pro workspaces: contact the administrator.
              </p>
            )}
            <div className="flex items-center gap-2 pt-1">
              <input
                type="text"
                readOnly
                value={createdInvite.invitation_url || `https://app.workspace.local/invitations?token=${createdInvite.token}`}
                className="flex-1 text-[12px] bg-white px-2.5 py-1.5 border border-[#99F6E4] rounded font-mono text-[#18181B] select-all"
              />
              <button
                type="button"
                onClick={() =>
                  copyToClipboard(createdInvite.invitation_url || `token:${createdInvite.token}`)
                }
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#99F6E4] hover:bg-[#CCFBF1] text-[#0F766E] text-[12px] font-medium rounded transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Invitations Tabs & Table */}
      <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
        <Tabs.List className="flex border-b border-[#E4E4E7] space-x-4 mb-4">
          <Tabs.Trigger
            value="pending"
            className="pb-2 text-[13px] font-medium text-[#71717A] data-[state=active]:text-[#0F766E] data-[state=active]:border-b-2 data-[state=active]:border-[#0F766E] focus:outline-none"
          >
            Pending
          </Tabs.Trigger>
          <Tabs.Trigger
            value="accepted"
            className="pb-2 text-[13px] font-medium text-[#71717A] data-[state=active]:text-[#0F766E] data-[state=active]:border-b-2 data-[state=active]:border-[#0F766E] focus:outline-none"
          >
            Accepted
          </Tabs.Trigger>
          <Tabs.Trigger
            value="revoked"
            className="pb-2 text-[13px] font-medium text-[#71717A] data-[state=active]:text-[#0F766E] data-[state=active]:border-b-2 data-[state=active]:border-[#0F766E] focus:outline-none"
          >
            Revoked
          </Tabs.Trigger>
        </Tabs.List>

        <div className="bg-white border border-[#E4E4E7] rounded-[6px] overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#E4E4E7] bg-[#FAFAFA] text-[12px] font-semibold text-[#71717A]">
                <th className="py-2.5 px-4">Invitee Email</th>
                <th className="py-2.5 px-4">Expires</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E4E4E7] text-[13px]">
              {isLoading ? (
                [1, 2].map((i) => (
                  <tr key={i}>
                    <td colSpan={3} className="py-3 px-4">
                      <div className="h-4 bg-[#E4E4E7]/60 rounded animate-pulse w-44" />
                    </td>
                  </tr>
                ))
              ) : invitations.length > 0 ? (
                invitations.map((inv) => (
                  <tr key={inv.id} className="hover:bg-[#FAFAFA] transition-colors">
                    <td className="py-3 px-4 font-medium text-[#18181B]">{inv.email}</td>
                    <td className="py-3 px-4 text-[#71717A] tabular-nums text-[12px]">
                      {new Date(inv.expires_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      {inv.status === "pending" && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleResend(inv.id)}
                            className="inline-flex items-center gap-1 text-[12px] text-[#71717A] hover:text-[#18181B] hover:underline"
                          >
                            <RotateCw className="w-3 h-3" />
                            <span>Resend</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleRevoke(inv.id)}
                            className="inline-flex items-center gap-1 text-[12px] text-[#DC2626] hover:underline"
                          >
                            <XCircle className="w-3 h-3" />
                            <span>Revoke</span>
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="py-6 text-center text-[#71717A]">
                    No {activeTab} invitations found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Tabs.Root>
    </div>
  );
};

