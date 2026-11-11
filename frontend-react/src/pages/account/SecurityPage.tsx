/**
 * Endpoints used by this page:
 * - GET /auth/sessions
 * - DELETE /auth/sessions/{session_id}
 * - POST /auth/logout-all
 * - POST /auth/change-password
 */
import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, Laptop, Globe, LogOut, KeyRound } from "lucide-react";
import { apiClient } from "../../shared/api/client.ts";
import type { SessionListResponse, SessionResponse } from "../../shared/api/types.ts";
import { useToast } from "../../shared/components/Toast.tsx";

export const SecurityPage: React.FC = () => {
  const { showToast } = useToast();

  // Password change state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Sessions query
  const { data: sessionData, isLoading, refetch } = useQuery<SessionListResponse>({
    queryKey: ["auth-sessions"],
    queryFn: async () => {
      const res = await apiClient.get<SessionListResponse>("/auth/sessions");
      return res.data;
    },
  });

  const sessions: SessionResponse[] = sessionData?.sessions || [];

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await apiClient.delete(`/auth/sessions/${sessionId}`);
      showToast("Session revoked.", "success");
      refetch();
    } catch {
      showToast("Failed to revoke session.", "error");
    }
  };

  const handleLogoutAll = async () => {
    try {
      await apiClient.post("/auth/logout-all");
      showToast("All other active sessions revoked.", "success");
      refetch();
    } catch {
      showToast("Failed to revoke other sessions.", "error");
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters long.");
      return;
    }

    setChangingPassword(true);
    try {
      await apiClient.post("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      showToast("Password updated successfully. Other sessions revoked.", "success");
      setCurrentPassword("");
      setNewPassword("");
      refetch();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setPasswordError(axiosErr.response?.data?.detail || "Failed to change password.");
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Security & Sessions</h1>
        <p className="text-[13px] text-[#71717A] mt-0.5">
          Manage active browser sessions, tokens, and account authentication credentials.
        </p>
      </div>

      {/* Active Sessions Card */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-[#E4E4E7]">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#0F766E]" />
            <h2 className="text-[14px] font-semibold text-[#18181B]">Active Devices & Sessions</h2>
          </div>
          <button
            type="button"
            onClick={handleLogoutAll}
            className="inline-flex items-center gap-1.5 px-3 py-1 text-[12px] font-medium border border-[#E4E4E7] text-[#DC2626] hover:bg-[#FEF2F2] rounded-[4px] transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign out all other devices</span>
          </button>
        </div>

        <div className="divide-y divide-[#E4E4E7]">
          {isLoading ? (
            <div className="py-4 text-center text-[#71717A] text-[13px]">Loading sessions...</div>
          ) : sessions.length > 0 ? (
            sessions.map((s) => (
              <div key={s.id} className="py-3 flex items-center justify-between text-[13px]">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded bg-[#F4F4F5] flex items-center justify-center text-[#71717A] shrink-0 mt-0.5">
                    <Laptop className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-[#18181B]">
                        {s.browser || "Browser"} on {s.platform || "Device"}
                      </span>
                      {s.is_current && (
                        <span className="px-1.5 py-0.2 text-[10px] font-semibold bg-[#F0FDFA] text-[#0F766E] border border-[#CCFBF1] rounded">
                          Current Device
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-[#71717A] mt-0.5">
                      <span className="flex items-center gap-1">
                        <Globe className="w-3 h-3" />
                        {s.ip_address || "Unknown IP"}
                      </span>
                      <span>•</span>
                      <span>Last active: {new Date(s.last_used_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {!s.is_current && (
                  <button
                    type="button"
                    onClick={() => handleRevokeSession(s.id)}
                    className="text-[12px] text-[#DC2626] hover:underline"
                  >
                    Revoke
                  </button>
                )}
              </div>
            ))
          ) : (
            <div className="py-4 text-center text-[#71717A] text-[13px]">No active sessions found.</div>
          )}
        </div>
      </div>

      {/* Change Password Card */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-5 space-y-4 shadow-sm">
        <div className="flex items-center gap-2 pb-3 border-b border-[#E4E4E7]">
          <KeyRound className="w-4 h-4 text-[#0F766E]" />
          <h2 className="text-[14px] font-semibold text-[#18181B]">Change Password</h2>
        </div>

        {passwordError && (
          <div className="p-2.5 bg-[#FEF2F2] border border-[#FEE2E2] rounded-[6px] text-[12px] text-[#DC2626]">
            {passwordError}
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-4 max-w-sm">
          <div>
            <label htmlFor="curr-password" className="block text-[12px] font-medium text-[#71717A] mb-1">
              Current Password
            </label>
            <input
              id="curr-password"
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full text-[13px] px-3 py-1.5 border border-[#E4E4E7] rounded-[6px] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
            />
          </div>

          <div>
            <label htmlFor="new-password" className="block text-[12px] font-medium text-[#71717A] mb-1">
              New Password (min 8 characters)
            </label>
            <input
              id="new-password"
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full text-[13px] px-3 py-1.5 border border-[#E4E4E7] rounded-[6px] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
            />
          </div>

          <button
            type="submit"
            disabled={changingPassword || !currentPassword || !newPassword}
            className="px-4 py-2 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] disabled:opacity-50 transition-colors"
          >
            {changingPassword ? "Updating Password..." : "Update Password"}
          </button>
        </form>
      </div>
    </div>
  );
};

