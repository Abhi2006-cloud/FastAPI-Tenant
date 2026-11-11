/**
 * Endpoints used by this page:
 * - PATCH /organizations/{id}
 * - DELETE /organizations/{id}
 * - GET /organizations/{id}
 */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient, getActiveOrgId } from "../../shared/api/client.ts";
import { useOrg } from "../../shared/context/OrgContext.tsx";
import { ConfirmDialog } from "../../shared/components/ConfirmDialog.tsx";
import { useToast } from "../../shared/components/Toast.tsx";

export const SettingsPage: React.FC = () => {
  const orgId = getActiveOrgId();
  const { activeOrg, role: myRole, refetchOrgs } = useOrg();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const isOwner = myRole === "owner";
  const isOwnerOrAdmin = myRole === "owner" || myRole === "admin";

  const [name, setName] = useState(activeOrg?.name || "");
  const [saving, setSaving] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const handleRename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !orgId) return;
    setSaving(true);
    try {
      await apiClient.patch(`/organizations/${orgId}`, { name: name.trim() });
      showToast("Workspace name updated.", "success");
      refetchOrgs();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      showToast(axiosErr.response?.data?.detail || "Failed to rename workspace.", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteOrg = async () => {
    if (!orgId || !activeOrg) return;
    try {
      await apiClient.delete(`/organizations/${orgId}`, {
        data: { name: activeOrg.name },
      });
      showToast("Workspace permanently deleted.", "success");
      refetchOrgs();
      navigate("/");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      showToast(axiosErr.response?.data?.detail || "Failed to delete workspace.", "error");
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Workspace Settings</h1>
        <p className="text-[13px] text-[#71717A] mt-0.5">
          General settings and workspace lifecycle operations.
        </p>
      </div>

      {/* General Settings: Rename */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-5 space-y-4 shadow-sm">
        <h2 className="text-[14px] font-semibold text-[#18181B]">General Information</h2>
        <form onSubmit={handleRename} className="space-y-4">
          <div>
            <label htmlFor="settings-org-name" className="block text-[12px] font-medium text-[#71717A] mb-1">
              Workspace Name
            </label>
            <input
              id="settings-org-name"
              type="text"
              disabled={!isOwnerOrAdmin}
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full text-[13px] px-3 py-1.5 border border-[#E4E4E7] rounded-[6px] focus:outline-none focus:ring-1 focus:ring-[#0F766E] disabled:bg-[#FAFAFA]"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            <span className="text-[12px] text-[#71717A]">
              Workspace ID: <code className="font-mono text-[#18181B]">{orgId}</code>
            </span>
            {isOwnerOrAdmin && (
              <button
                type="submit"
                disabled={saving || !name.trim()}
                className="px-4 py-1.5 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] disabled:opacity-50 transition-colors"
              >
                {saving ? "Saving..." : "Save Changes"}
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Danger Zone: Delete Organization */}
      <div className="bg-white border border-[#FEE2E2] rounded-[6px] p-5 space-y-3">
        <h2 className="text-[14px] font-semibold text-[#DC2626]">Danger Zone</h2>
        <p className="text-[12px] text-[#52525B]">
          Permanently delete this organization, including all member associations, files, and historical audit logs. This action cannot be reversed.
        </p>

        <div className="pt-2">
          {isOwner ? (
            <button
              type="button"
              onClick={() => setDeleteDialogOpen(true)}
              className="px-3 py-1.5 bg-[#DC2626] hover:bg-[#B91C1C] text-white text-[12px] font-medium rounded-[6px] transition-colors"
            >
              Delete Organization
            </button>
          ) : (
            <span className="text-[12px] text-[#71717A]">
              Only the workspace owner ({activeOrg?.owner_id}) can delete this organization.
            </span>
          )}
        </div>
      </div>

      {/* Confirm Delete Dialog with exact name typed confirmation */}
      {activeOrg && (
        <ConfirmDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          title="Delete Organization"
          description={`This action will permanently delete "${activeOrg.name}" and all associated tenant data. Type the workspace name below to confirm.`}
          confirmWord={activeOrg.name}
          confirmButtonText="Delete Organization"
          isDestructive={true}
          onConfirm={handleDeleteOrg}
        />
      )}
    </div>
  );
};

