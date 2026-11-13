/**
 * Endpoints used by this page:
 * - GET /organizations/{id}/members
 * - PATCH /organizations/{id}/members/{id}/role
 * - DELETE /organizations/{id}/members/{id}
 * - POST /organizations/{id}/transfer_ownership
 * - POST /organizations/{id}/leave
 */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { UserMinus, ArrowRightLeft, LogOut } from "lucide-react";
import { apiClient, getActiveOrgId } from "../../shared/api/client.ts";
import { useOrg } from "../../shared/context/OrgContext.tsx";
import { useAuth } from "../../shared/context/AuthContext.tsx";
import type { MemberListResponse } from "../../shared/api/types.ts";
import { ConfirmDialog } from "../../shared/components/ConfirmDialog.tsx";
import { useToast } from "../../shared/components/Toast.tsx";

type MemberItem = MemberListResponse;

export const MembersPage: React.FC = () => {
  const orgId = getActiveOrgId();
  const { activeOrg, role: myRole, refetchOrgs } = useOrg();
  const { user } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const isOwner = myRole === "owner";

  // Selected action targets for confirm dialogs
  const [memberToRemove, setMemberToRemove] = useState<MemberItem | null>(null);
  const [memberToTransfer, setMemberToTransfer] = useState<MemberItem | null>(null);
  const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);

  // Fetch members list
  const { data: members = [], isLoading, refetch } = useQuery<MemberListResponse[]>({
    queryKey: ["members", orgId],
    queryFn: async () => {
      if (!orgId) throw new Error("No active org");
      const res = await apiClient.get<MemberListResponse[]>(`/organizations/${orgId}/members`);
      return res.data;
    },
    enabled: !!orgId,
  });

  // Role Change handler
  const handleRoleChange = async (membershipId: string, newRole: "admin" | "member") => {
    try {
      await apiClient.patch(`/organizations/${orgId}/members/${membershipId}/role`, {
        role: newRole,
      });
      showToast("Member role updated.", "success");
      refetch();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      showToast(axiosErr.response?.data?.detail || "Failed to update member role.", "error");
    }
  };

  // Remove Member handler
  const handleRemoveMember = async () => {
    if (!memberToRemove || !orgId) return;
    try {
      await apiClient.delete(`/organizations/${orgId}/members/${memberToRemove.membership_id}`);
      showToast(`Removed ${memberToRemove.email} from workspace.`, "success");
      refetch();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      showToast(axiosErr.response?.data?.detail || "Failed to remove member.", "error");
    } finally {
      setMemberToRemove(null);
    }
  };

  // Transfer Ownership handler
  const handleTransferOwnership = async () => {
    if (!memberToTransfer || !orgId) return;
    try {
      await apiClient.post(`/organizations/${orgId}/transfer-ownership`, {
        new_owner_membership_id: memberToTransfer.membership_id,
        new_owner_user_id: memberToTransfer.user_id,
      });
      showToast(`Ownership transferred to ${memberToTransfer.email}.`, "success");
      refetch();
      refetchOrgs();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      showToast(axiosErr.response?.data?.detail || "Failed to transfer ownership.", "error");
    } finally {
      setMemberToTransfer(null);
    }
  };

  // Leave Org handler
  const handleLeaveOrg = async () => {
    if (!orgId) return;
    try {
      await apiClient.post(`/organizations/${orgId}/leave`);
      showToast("You have left the organization.", "success");
      refetchOrgs();
      navigate("/");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      showToast(axiosErr.response?.data?.detail || "Failed to leave workspace.", "error");
    } finally {
      setLeaveDialogOpen(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Workspace Members</h1>
          <p className="text-[13px] text-[#71717A] mt-0.5">
            Manage member roles and tenant access boundaries.
          </p>
        </div>
        {!isOwner && (
          <button
            type="button"
            onClick={() => setLeaveDialogOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium border border-[#E4E4E7] text-[#DC2626] hover:bg-[#FEF2F2] rounded-[6px] transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Leave Workspace</span>
          </button>
        )}
      </div>

      {/* Members Table */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#E4E4E7] bg-[#FAFAFA] text-[12px] font-semibold text-[#71717A]">
              <th className="py-2.5 px-4">Member Email</th>
              <th className="py-2.5 px-4">Role</th>
              <th className="py-2.5 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E4E4E7] text-[13px]">
            {isLoading ? (
              [1, 2, 3].map((i) => (
                <tr key={i}>
                  <td colSpan={3} className="py-3 px-4">
                    <div className="h-4 bg-[#E4E4E7]/60 rounded animate-pulse w-48" />
                  </td>
                </tr>
              ))
            ) : members.length > 0 ? (
              members.map((m) => {
                const isSelf = m.user_id === user?.id;
                const isMemberOwner = m.role === "owner";

                return (
                  <tr key={m.membership_id} className="hover:bg-[#FAFAFA] transition-colors">
                    <td className="py-3 px-4 font-medium text-[#18181B]">
                      {m.email} {isSelf && <span className="text-[#71717A] text-[11px] font-normal">(You)</span>}
                    </td>
                    <td className="py-3 px-4">
                      {isOwner && !isMemberOwner && !isSelf ? (
                        <select
                          value={m.role}
                          onChange={(e) =>
                            handleRoleChange(m.membership_id, e.target.value as "admin" | "member")
                          }
                          className="text-[12px] py-1 px-2 border border-[#E4E4E7] rounded-[4px] bg-white text-[#18181B] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
                        >
                          <option value="admin">admin</option>
                          <option value="member">member</option>
                        </select>
                      ) : (
                        <span className="capitalize px-2 py-0.5 text-[11px] font-medium bg-[#F4F4F5] text-[#52525B] rounded-[4px] border border-[#E4E4E7]">
                          {m.role}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      {isOwner && !isMemberOwner && !isSelf ? (
                        <>
                          <button
                            type="button"
                            onClick={() => setMemberToTransfer(m)}
                            className="inline-flex items-center gap-1 text-[12px] text-[#71717A] hover:text-[#18181B] hover:underline"
                          >
                            <ArrowRightLeft className="w-3 h-3" />
                            <span>Transfer Ownership</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => setMemberToRemove(m)}
                            className="inline-flex items-center gap-1 text-[12px] text-[#DC2626] hover:underline"
                          >
                            <UserMinus className="w-3 h-3" />
                            <span>Remove</span>
                          </button>
                        </>
                      ) : !isOwner && !isSelf ? (
                        <span className="text-[11px] text-[#A1A1AA]" title="Only the workspace owner can manage members">
                          Owner only
                        </span>
                      ) : null}
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={3} className="py-6 text-center text-[#71717A]">
                  No members found in this workspace.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Confirm Dialog: Remove Member */}
      {memberToRemove && (
        <ConfirmDialog
          open={!!memberToRemove}
          onOpenChange={(open) => !open && setMemberToRemove(null)}
          title="Remove Workspace Member"
          description={`Are you sure you want to remove ${memberToRemove.email}? They will immediately lose access to all files and data in this organization.`}
          confirmWord={memberToRemove.email}
          confirmButtonText="Remove Member"
          onConfirm={handleRemoveMember}
        />
      )}

      {/* Confirm Dialog: Transfer Ownership */}
      {memberToTransfer && (
        <ConfirmDialog
          open={!!memberToTransfer}
          onOpenChange={(open) => !open && setMemberToTransfer(null)}
          title="Transfer Workspace Ownership"
          description={`Transferring ownership to ${memberToTransfer.email} is irreversible. You will become an admin in this workspace.`}
          confirmWord={memberToTransfer.email}
          confirmButtonText="Transfer Ownership"
          isDestructive={true}
          onConfirm={handleTransferOwnership}
        />
      )}

      {/* Confirm Dialog: Leave Workspace */}
      <ConfirmDialog
        open={leaveDialogOpen}
        onOpenChange={setLeaveDialogOpen}
        title="Leave Workspace"
        description={`Are you sure you want to leave ${activeOrg?.name}? You will need an invitation from an owner or admin to regain access.`}
        confirmWord={activeOrg?.name}
        confirmButtonText="Leave Workspace"
        onConfirm={handleLeaveOrg}
      />
    </div>
  );
};
