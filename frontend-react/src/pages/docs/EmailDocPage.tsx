import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, AlertCircle } from "lucide-react";

export const EmailDocPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <Link to="/platform" className="inline-flex items-center gap-1.5 text-[12px] text-[#0F766E] hover:underline mb-2">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Platform Status</span>
        </Link>
        <div className="flex items-center justify-between">
          <h1 className="text-[20px] font-semibold text-[#18181B] tracking-tight">
            Email Delivery Architecture
          </h1>
          <span className="px-2 py-0.5 text-[11px] font-medium tracking-wide bg-[#F4F4F5] text-[#71717A] border border-[#E4E4E7] rounded-[4px]">
            Paid feature, not enabled on this deployment
          </span>
        </div>
        <p className="text-[13px] text-[#71717A] mt-1">
          Technical specifications for background email scheduling, Jinja2 templating, and retry strategies.
        </p>
      </div>

      <div className="p-4 bg-[#FFFBEB] border border-[#FEF3C7] rounded-[6px] text-[12px] text-[#92400E] flex items-start gap-2.5">
        <AlertCircle className="w-4 h-4 shrink-0 text-[#D97706] mt-0.5" />
        <p>
          Live email delivery via Resend requires a custom DNS verified domain. To maintain a strict zero-cost deployment, the backend runs in <code className="font-mono">console</code> mode and provides invitation tokens directly in the UI (<code className="font-mono">delivery_mode: manual</code>).
        </p>
      </div>

      {/* Architecture Diagram (SVG) */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-6 shadow-sm space-y-4">
        <h2 className="text-[14px] font-semibold text-[#18181B]">Email Pipeline & State Machine</h2>
        <div className="bg-[#FAFAFA] border border-[#E4E4E7] rounded-[6px] p-4 flex justify-center">
          <svg className="w-full max-w-xl" viewBox="0 0 600 200" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Box 1: Enqueue */}
            <rect x="20" y="30" width="120" height="50" rx="4" fill="#FFFFFF" stroke="#E4E4E7" strokeWidth="1.5" />
            <text x="80" y="52" textAnchor="middle" fill="#18181B" fontSize="11" fontWeight="600">EmailService</text>
            <text x="80" y="68" textAnchor="middle" fill="#71717A" fontSize="9">State: QUEUED</text>

            {/* Arrow 1 */}
            <path d="M140 55 H180" stroke="#0F766E" strokeWidth="1.5" />

            {/* Box 2: RQ Queue */}
            <rect x="190" y="30" width="120" height="50" rx="4" fill="#FFFFFF" stroke="#E4E4E7" strokeWidth="1.5" />
            <text x="250" y="52" textAnchor="middle" fill="#18181B" fontSize="11" fontWeight="600">RQ Worker</text>
            <text x="250" y="68" textAnchor="middle" fill="#71717A" fontSize="9">State: PROCESSING</text>

            {/* Arrow 2 */}
            <path d="M310 55 H350" stroke="#0F766E" strokeWidth="1.5" />

            {/* Box 3: Provider (Resend / Console) */}
            <rect x="360" y="30" width="120" height="50" rx="4" fill="#F0FDFA" stroke="#0F766E" strokeWidth="1.5" />
            <text x="420" y="52" textAnchor="middle" fill="#0F766E" fontSize="11" fontWeight="600">Provider API</text>
            <text x="420" y="68" textAnchor="middle" fill="#115E59" fontSize="9">State: SENT</text>

            {/* Retry branch */}
            <path d="M420 80 V130 H250 V80" stroke="#DC2626" strokeWidth="1.5" strokeDasharray="3 3" />
            <rect x="280" y="115" width="140" height="30" rx="4" fill="#FEF2F2" stroke="#FCA5A5" />
            <text x="350" y="134" textAnchor="middle" fill="#DC2626" fontSize="10">Retry: 30s / 120s / 600s / 1800s / 3600s</text>

            {/* Final Box 4: FAILED / CANCELLED */}
            <rect x="490" y="105" width="100" height="50" rx="4" fill="#FEF2F2" stroke="#DC2626" strokeWidth="1.5" />
            <text x="540" y="128" textAnchor="middle" fill="#DC2626" fontSize="11" fontWeight="600">Max Retries</text>
            <text x="540" y="144" textAnchor="middle" fill="#991B1B" fontSize="9">State: FAILED</text>
            <path d="M420 130 H490" stroke="#DC2626" strokeWidth="1.5" />
          </svg>
        </div>
      </div>

      {/* Technical Specifications */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-6 shadow-sm space-y-4 text-[13px] text-[#52525B] leading-relaxed">
        <h2 className="text-[14px] font-semibold text-[#18181B]">Implementation Details (Audit Sections 8.3 & 13.2)</h2>
        <ul className="space-y-2 list-disc pl-5">
          <li>
            <strong className="text-[#18181B]">Template Engine:</strong> Jinja2 compiles responsive HTML and plaintext fallback templates from <code className="font-mono text-[#18181B]">app/infrastructure/email/templates/</code> with token interpolation.
          </li>
          <li>
            <strong className="text-[#18181B]">Retry Schedule:</strong> Failed delivery attempts follow an exponential backoff schedule: 30s, 120s, 600s, 1800s, and 3600s.
          </li>
          <li>
            <strong className="text-[#18181B]">Rate Limiting:</strong> Redis token bucket enforces an hourly rate limit (default 20 emails/hour) per organization to prevent mailbox flooding.
          </li>
          <li>
            <strong className="text-[#18181B]">State Tracking:</strong> Every email lifecycle transitions across native PostgreSQL enum states: <code className="font-mono text-[#18181B]">QUEUED</code> → <code className="font-mono text-[#18181B]">PROCESSING</code> → <code className="font-mono text-[#18181B]">SENT</code> or <code className="font-mono text-[#18181B]">FAILED</code>.
          </li>
        </ul>
      </div>
    </div>
  );
};
