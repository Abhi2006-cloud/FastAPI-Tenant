/**
 * Endpoints used by this page:
 * - GET /organizations/{id}/invitations
 * - POST /organizations/{id}/invite
 * - POST /invitations/{id}/resend
 * - DELETE /organizations/{id}/invitations/{id}
 * - POST /invitations/accept
 */
import React, { useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { useQuery } from "@tanstack/react-query";
import { UserPlus, Copy, Check, RotateCw, XCircle, Info, KeyRound, ArrowRight, Loader2 } from "lucide-react";
import { apiClient, getActiveOrgId } from "../../shared/api/client.ts";
import { useOrg } from "../../shared/context/OrgContext.tsx";
import type { InvitationResponse } from "../../shared/api/types.ts";
import { LimitMeter } from "../../shared/components/LimitMeter.tsx";
import { useToast } from "../../shared/components/Toast.tsx";

export const InvitationsPage: React.FC = () => {
  const orgId = getActiveOrgId();
  const { role: myRole, refetchOrgs, switchOrg } = useOrg();
  const { showToast } = useToast();

  const isOwnerOrAdmin = myRole === "owner" || myRole === "admin";

  // Create invite state
  const [emailInput, setEmailInput] = useState("");
  const [inviting, setInviting] = useState(false);
  const [createdInvite, setCreatedInvite] = useState<InvitationResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState("pending");

  // Accept invite state
  const [acceptTokenInput, setAcceptTokenInput] = useState("");
  const [accepting, setAccepting] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);

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

  const handleAcceptInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    let token = acceptTokenInput.trim();
    if (token.includes("token=")) {
      try {
        const url = new URL(token, window.location.origin);
        const parsed = url.searchParams.get("token");
        if (parsed) token = parsed.trim();
      } catch {
        const match = token.match(/token=([a-zA-Z0-9_-]+)/);
        if (match) token = match[1];
      }
    }
    if (!token) return;

    setAccepting(true);
    setAcceptError(null);
    try {
      const res = await apiClient.post<InvitationResponse>("/invitations/accept", { token });
      showToast("Invitation accepted! You have joined the workspace.", "success");
      setAcceptTokenInput("");
      refetchOrgs();
      if (res.data.organization_id) {
        switchOrg(res.data.organization_id);
      }
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: {
          data?: {
            detail?: string | { code?: string };
          };
        };
      };
      const d = axiosErr.response?.data?.detail;
      const msg = typeof d === "string" ? d : "Failed to accept invitation. Please check the token.";
      setAcceptError(msg);
      showToast(msg, "error");
    } finally {
      setAccepting(false);
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

  const renderAcceptCard = () => (
    <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-5 space-y-3 shadow-sm">
      <div className="flex items-center gap-2 pb-2 border-b border-[#E4E4E7]">
        <KeyRound className="w-4 h-4 text-[#0F766E]" />
        <h2 className="text-[14px] font-semibold text-[#18181B]">Accept an Invitation</h2>
      </div>
      <p className="text-[12px] text-[#71717A]">
        Received an invitation token or join link from another workspace? Paste it below to join their organization.
      </p>

      {acceptError && (
        <div className="p-2.5 bg-[#FEF2F2] border border-[#FEE2E2] rounded-[6px] text-[12px] text-[#DC2626]">
          {acceptError}
        </div>
      )}

      <form onSubmit={handleAcceptInvite} className="flex gap-2">
        <input
          type="text"
          required
          value={acceptTokenInput}
          onChange={(e) => setAcceptTokenInput(e.target.value)}
          placeholder="Paste invitation token or join URL here..."
          className="flex-1 text-[13px] px-3 py-1.5 border border-[#E4E4E7] rounded-[6px] font-mono focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
        />
        <button
          type="submit"
          disabled={accepting || !acceptTokenInput.trim()}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] disabled:opacity-50 transition-colors"
        >
          {accepting ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Joining...</span>
            </>
          ) : (
            <>
              <span>Join Workspace</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </form>
    </div>
  );

  if (!isOwnerOrAdmin) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Invitations</h1>
          <p className="text-[13px] text-[#71717A] mt-0.5">
            Accept invitations to join other workspaces.
          </p>
        </div>

        {/* Accept an Invitation Card */}
        {renderAcceptCard()}

        <div className="p-6 bg-white border border-[#E4E4E7] rounded-[6px] text-center space-y-1.5">
          <h2 className="text-[14px] font-medium text-[#18181B]">Team Invitations</h2>
          <p className="text-[12px] text-[#71717A] max-w-[420px] mx-auto">
            You are a member of this workspace. To invite new teammates to this workspace, please contact a workspace Owner or Admin.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Invitations</h1>
        <p className="text-[13px] text-[#71717A] mt-0.5">
          Invite teammates into this tenant workspace or accept invitations from other workspaces.
        </p>
      </div>

      {/* Accept an Invitation Card */}
      {renderAcceptCard()}

      {/* Invite Creation Card */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between pb-2 border-b border-[#E4E4E7]">
          <div className="flex items-center gap-2">
            <UserPlus className="w-4 h-4 text-[#0F766E]" />
            <h2 className="text-[14px] font-semibold text-[#18181B]">Invite Teammate to Current Workspace</h2>
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
                Workspace is on the free tier. Share the invitation link directly with your teammate:
              </p>
            )}
            {createdInvite.delivery_mode === "development" && (
              <p className="text-[12px] text-[#115E59]">
                Backend is running with console email delivery. Copy and share the invitation link below:
              </p>
            )}

            {createdInvite.invitation_url && (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={createdInvite.invitation_url}
                  className="flex-1 text-[12px] px-2.5 py-1.5 bg-white border border-[#CCFBF1] rounded font-mono text-[#0F766E]"
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(createdInvite.invitation_url!)}
                  className="px-3 py-1.5 bg-[#0F766E] hover:bg-[#115E59] text-white text-[12px] rounded flex items-center gap-1.5"
                >
                  {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copied" : "Copy Link"}</span>
                </button>
              </div>
            )}

            {createdInvite.token && (
              <p className="text-[11px] text-[#0F766E]/80 font-mono">
                Token: {createdInvite.token}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Invitations List Table */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] shadow-sm overflow-hidden">
        <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
          <div className="border-b border-[#E4E4E7] px-4 pt-2">
            <Tabs.List className="flex gap-4">
              <Tabs.Trigger
                value="pending"
                className={`pb-2.5 text-[13px] font-medium transition-colors border-b-2 -mb-px ${activeTab === "pending"
                    ? "border-[#0F766E] text-[#0F766E]"
                    : "border-transparent text-[#71717A] hover:text-[#18181B]"
                  }`}
              >
                Pending
              </Tabs.Trigger>
              <Tabs.Trigger
                value="accepted"
                className={`pb-2.5 text-[13px] font-medium transition-colors border-b-2 -mb-px ${activeTab === "accepted"
                    ? "border-[#0F766E] text-[#0F766E]"
                    : "border-transparent text-[#71717A] hover:text-[#18181B]"
                  }`}
              >
                Accepted
              </Tabs.Trigger>
              <Tabs.Trigger
                value="revoked"
                className={`pb-2.5 text-[13px] font-medium transition-colors border-b-2 -mb-px ${activeTab === "revoked"
                    ? "border-[#0F766E] text-[#0F766E]"
                    : "border-transparent text-[#71717A] hover:text-[#18181B]"
                  }`}
              >
                Revoked
              </Tabs.Trigger>
            </Tabs.List>
          </div>

          <Tabs.Content value={activeTab} className="p-0">
            {isLoading ? (
              <div className="p-8 text-center text-[13px] text-[#71717A]">
                Loading invitations...
              </div>
            ) : invitations.length === 0 ? (
              <div className="p-8 text-center text-[13px] text-[#71717A]">
                No {activeTab} invitations found.
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#E4E4E7] bg-[#FAFAFA] text-[11px] font-semibold text-[#71717A] uppercase tracking-wider">
                    <th className="py-2.5 px-4">Invitee Email</th>
                    <th className="py-2.5 px-4">Role</th>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4">Expires</th>
                    <th className="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7] text-[13px]">
                  {invitations.map((inv) => (
                    <tr key={inv.id} className="hover:bg-[#FAFAFA]">
                      <td className="py-3 px-4 font-medium text-[#18181B]">
                        {inv.email}
                      </td>
                      <td className="py-3 px-4 text-[#52525B] capitalize">
                        member
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium capitalize ${inv.status === "pending"
                              ? "bg-[#FEF3C7] text-[#92400E]"
                              : inv.status === "accepted"
                                ? "bg-[#DCFCE7] text-[#166534]"
                                : "bg-[#F4F4F5] text-[#71717A]"
                            }`}
                        >
                          {inv.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-[12px] text-[#71717A]">
                        {new Date(inv.expires_at).toLocaleDateString([], {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {inv.status === "pending" && (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => handleResend(inv.id)}
                              title="Resend invitation email"
                              className="p-1 text-[#71717A] hover:text-[#0F766E] rounded hover:bg-[#F4F4F5]"
                            >
                              <RotateCw className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => handleRevoke(inv.id)}
                              title="Revoke invitation"
                              className="p-1 text-[#71717A] hover:text-[#DC2626] rounded hover:bg-[#F4F4F5]"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Tabs.Content>
        </Tabs.Root>
      </div>
    </div>
  );
};
