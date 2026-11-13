/**
 * Endpoints used by this page:
 * - POST /invitations/accept
 */
import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { KeyRound, Loader2, Building2, ArrowRight } from "lucide-react";
import { apiClient } from "../../shared/api/client.ts";
import { useAuth } from "../../shared/context/AuthContext.tsx";
import { useOrg } from "../../shared/context/OrgContext.tsx";
import { useToast } from "../../shared/components/Toast.tsx";
import type { InvitationResponse } from "../../shared/api/types.ts";

export const AcceptInvitePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, isLoading: authLoading } = useAuth();
  const { refetchOrgs, switchOrg } = useOrg();
  const { showToast } = useToast();

  const queryToken = searchParams.get("token") || "";
  const [tokenInput, setTokenInput] = useState(queryToken);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (queryToken) {
      setTokenInput(queryToken);
      sessionStorage.setItem("pending_invite_token", queryToken);
    }
  }, [queryToken]);

  const handleAccept = async (e: React.FormEvent) => {
    e.preventDefault();
    let token = tokenInput.trim();
    if (!token) return;

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

    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.post<InvitationResponse>("/invitations/accept", { token });
      sessionStorage.removeItem("pending_invite_token");
      showToast("Invitation accepted! You have joined the workspace.", "success");
      await refetchOrgs();
      if (res.data?.organization_id) {
        switchOrg(res.data.organization_id);
        navigate(`/o/${res.data.organization_id}/overview`);
      } else {
        navigate("/");
      }
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: {
          data?: {
            detail?: string | { code?: string; message?: string };
          };
        };
      };
      const detail = axiosErr.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : typeof detail === "object" && detail?.message
          ? detail.message
          : "Failed to accept invitation. The invitation may be invalid, expired, or already used.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center">
        <div className="h-6 w-24 bg-[#E4E4E7]/60 rounded animate-pulse" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-[440px] bg-white border border-[#E4E4E7] rounded-[6px] p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-[#E4E4E7]">
          <KeyRound className="w-4 h-4 text-[#0F766E]" />
          <h1 className="text-[15px] font-semibold text-[#18181B]">Join Workspace</h1>
        </div>

        {user ? (
          <div className="text-[12px] text-[#52525B]">
            Accepting invitation as <span className="font-medium text-[#18181B]">{user.email}</span>
          </div>
        ) : (
          <div className="p-3 bg-[#F4F4F5] border border-[#E4E4E7] rounded-[6px] text-[12px] text-[#52525B] space-y-2">
            <p>You need to sign in or create an account to accept this workspace invitation.</p>
            <div className="flex items-center gap-2 pt-1">
              <Link
                to={`/login${tokenInput ? `?redirect=/invitations?token=${encodeURIComponent(tokenInput)}` : ""}`}
                className="px-3 py-1 bg-[#0F766E] text-white text-[12px] font-medium rounded hover:bg-[#115E59]"
              >
                Sign In
              </Link>
              <Link
                to={`/register${tokenInput ? `?redirect=/invitations?token=${encodeURIComponent(tokenInput)}` : ""}`}
                className="px-3 py-1 border border-[#E4E4E7] text-[#18181B] text-[12px] font-medium rounded hover:bg-[#FAFAFA]"
              >
                Create Account
              </Link>
            </div>
          </div>
        )}

        {error && (
          <div className="p-2.5 bg-[#FEF2F2] border border-[#FEE2E2] rounded-[6px] text-[12px] text-[#DC2626]">
            {error}
          </div>
        )}

        <form onSubmit={handleAccept} className="space-y-4">
          <div>
            <label htmlFor="invite-token" className="block text-[12px] font-medium text-[#71717A] mb-1">
              Invitation Token
            </label>
            <input
              id="invite-token"
              type="text"
              required
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Paste the invitation token or full invitation link..."
              className="w-full px-3 py-2 border border-[#E4E4E7] rounded-[6px] text-[13px] text-[#18181B] placeholder-[#A1A1AA] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E] font-mono text-[12px]"
            />
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-[#E4E4E7]">
            <Link
              to="/o/new"
              className="inline-flex items-center gap-1 text-[12px] text-[#0F766E] hover:underline"
            >
              <Building2 className="w-3.5 h-3.5" />
              <span>Create new workspace instead</span>
            </Link>
            <button
              type="submit"
              disabled={loading || !tokenInput.trim() || !user}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] disabled:opacity-50 transition-colors"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Joining...</span>
                </>
              ) : (
                <>
                  <span>Accept &amp; Join</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

