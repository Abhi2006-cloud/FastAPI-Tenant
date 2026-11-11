/**
 * Endpoints used by this page:
 * - POST /auth/register
 * - POST /auth/login
 * - POST /demo/session
 */
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";
import { useAuth } from "../../shared/context/AuthContext.tsx";

export const RegisterPage: React.FC = () => {
  const { register, startDemoSession } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await register(email, password);
      navigate("/o/new");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail || "Registration failed. Email may already be in use.");
    } finally {
      setLoading(false);
    }
  };

  const handleDemo = async () => {
    setError(null);
    setDemoLoading(true);
    try {
      const demoRes = await startDemoSession();
      navigate(`/o/${demoRes.organization_id}/overview`);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail || "Could not provision demo session.");
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-[360px] space-y-6">
        <div>
          <h1 className="text-[20px] font-semibold text-[#18181B] tracking-tight">Create Workspace Account</h1>
          <p className="text-[13px] text-[#71717A] mt-1">Deployable multi-tenant backend architecture</p>
        </div>

        <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-6 shadow-sm space-y-4">
          {error && (
            <div className="p-2.5 bg-[#FEF2F2] border border-[#FEE2E2] rounded-[6px] text-[12px] text-[#DC2626]">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div>
              <label htmlFor="reg-email" className="block text-[12px] font-medium text-[#71717A] mb-1">
                Work Email
              </label>
              <input
                id="reg-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full text-[13px] px-3 py-1.5 border border-[#E4E4E7] rounded-[6px] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
                placeholder="developer@example.com"
              />
            </div>

            <div>
              <label htmlFor="reg-password" className="block text-[12px] font-medium text-[#71717A] mb-1">
                Password
              </label>
              <input
                id="reg-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full text-[13px] px-3 py-1.5 border border-[#E4E4E7] rounded-[6px] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
                placeholder="At least 8 characters"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] transition-colors disabled:opacity-50"
            >
              {loading ? "Creating account..." : "Register"}
            </button>
          </form>

          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[#E4E4E7]" />
            </div>
            <div className="relative flex justify-center text-[11px] uppercase tracking-wider text-[#A1A1AA]">
              <span className="bg-white px-2">or</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleDemo}
            disabled={demoLoading}
            className="w-full py-2 bg-[#F0FDFA] hover:bg-[#CCFBF1] text-[#0F766E] border border-[#99F6E4] text-[13px] font-medium rounded-[6px] flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{demoLoading ? "Creating demo workspace..." : "Try the interactive demo"}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="text-center text-[12px] text-[#71717A]">
          Already have an account?{" "}
          <Link to="/login" className="text-[#0F766E] hover:underline font-medium">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
};
