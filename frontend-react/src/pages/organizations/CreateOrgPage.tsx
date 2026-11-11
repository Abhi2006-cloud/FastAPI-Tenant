/**
 * Endpoints used by this page:
 * - POST /organizations
 */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Building2 } from "lucide-react";
import { apiClient } from "../../shared/api/client.ts";
import { useOrg } from "../../shared/context/OrgContext.tsx";
import type { OrganizationResponse } from "../../shared/api/types.ts";

export const CreateOrgPage: React.FC = () => {
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { refetchOrgs } = useOrg();

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.post<OrganizationResponse>("/organizations", { name: name.trim() });
      refetchOrgs();
      navigate(`/o/${res.data.id}/overview`);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail || "Failed to create workspace.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-[400px] bg-white border border-[#E4E4E7] rounded-[6px] p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-[#E4E4E7]">
          <Building2 className="w-4 h-4 text-[#0F766E]" />
          <h1 className="text-[15px] font-semibold text-[#18181B]">Create New Workspace</h1>
        </div>

        {error && (
          <div className="p-2.5 bg-[#FEF2F2] border border-[#FEE2E2] rounded-[6px] text-[12px] text-[#DC2626]">
            {error}
          </div>
        )}

        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label htmlFor="workspace-name" className="block text-[12px] font-medium text-[#71717A] mb-1">
              Workspace Name
            </label>
            <input
              id="workspace-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Acme Engineering"
              className="w-full text-[13px] px-3 py-1.5 border border-[#E4E4E7] rounded-[6px] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="px-3 py-1.5 border border-[#E4E4E7] text-[13px] text-[#52525B] hover:bg-[#FAFAFA] rounded-[6px]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-1.5 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create Workspace"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

