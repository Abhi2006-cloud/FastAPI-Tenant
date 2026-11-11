import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, AlertCircle } from "lucide-react";

export const SearchDocPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <Link to="/platform" className="inline-flex items-center gap-1.5 text-[12px] text-[#0F766E] hover:underline mb-2">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Platform Status</span>
        </Link>
        <div className="flex items-center justify-between">
          <h1 className="text-[20px] font-semibold text-[#18181B] tracking-tight">
            Search Architecture & Indexing
          </h1>
          <span className="px-2 py-0.5 text-[11px] font-medium tracking-wide bg-[#F4F4F5] text-[#71717A] border border-[#E4E4E7] rounded-[4px]">
            Paid feature, not enabled on this deployment
          </span>
        </div>
        <p className="text-[13px] text-[#71717A] mt-1">
          Technical specifications for the decoupled Meilisearch cluster, indexing queue, and circuit breaker.
        </p>
      </div>

      <div className="p-4 bg-[#FFFBEB] border border-[#FEF3C7] rounded-[6px] text-[12px] text-[#92400E] flex items-start gap-2.5">
        <AlertCircle className="w-4 h-4 shrink-0 text-[#D97706] mt-0.5" />
        <p>
          Meilisearch Cloud trial has concluded for this deployment. The system gracefully falls back to PostgreSQL case-insensitive pattern matching (<code className="font-mono">GET /search/basic</code>) so all search capabilities remain active with zero recurring fees.
        </p>
      </div>

      {/* Architecture Diagram (SVG) */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-6 shadow-sm space-y-4">
        <h2 className="text-[14px] font-semibold text-[#18181B]">Search Pipeline Architecture</h2>
        <div className="bg-[#FAFAFA] border border-[#E4E4E7] rounded-[6px] p-4 flex justify-center">
          <svg className="w-full max-w-xl" viewBox="0 0 600 220" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Box 1: Mutation (DB) */}
            <rect x="20" y="20" width="140" height="60" rx="4" fill="#FFFFFF" stroke="#E4E4E7" strokeWidth="1.5" />
            <text x="90" y="45" textAnchor="middle" fill="#18181B" fontSize="12" fontWeight="600">FastAPI Mutation</text>
            <text x="90" y="62" textAnchor="middle" fill="#71717A" fontSize="10">PostgreSQL Commit</text>

            {/* Arrow 1 */}
            <path d="M160 50 H210" stroke="#0F766E" strokeWidth="1.5" markerEnd="url(#arrow)" />

            {/* Box 2: RQ Queue */}
            <rect x="220" y="20" width="140" height="60" rx="4" fill="#FFFFFF" stroke="#E4E4E7" strokeWidth="1.5" />
            <text x="290" y="45" textAnchor="middle" fill="#18181B" fontSize="12" fontWeight="600">Async RQ Task</text>
            <text x="290" y="62" textAnchor="middle" fill="#71717A" fontSize="10">Redis Queue (search)</text>

            {/* Arrow 2 */}
            <path d="M360 50 H410" stroke="#0F766E" strokeWidth="1.5" />

            {/* Box 3: Meilisearch */}
            <rect x="420" y="20" width="160" height="60" rx="4" fill="#F0FDFA" stroke="#0F766E" strokeWidth="1.5" />
            <text x="500" y="45" textAnchor="middle" fill="#0F766E" fontSize="12" fontWeight="600">Meilisearch Cluster</text>
            <text x="500" y="62" textAnchor="middle" fill="#115E59" fontSize="10">filter: organization_id</text>

            {/* Circuit breaker fallback branch */}
            <path d="M290 80 V140 H160" stroke="#DC2626" strokeWidth="1.5" strokeDasharray="4 4" />

            {/* Box 4: Dead-Letter Failures */}
            <rect x="20" y="120" width="140" height="60" rx="4" fill="#FEF2F2" stroke="#FCA5A5" strokeWidth="1.5" />
            <text x="90" y="145" textAnchor="middle" fill="#DC2626" fontSize="12" fontWeight="600">Failure Dead-Letter</text>
            <text x="90" y="162" textAnchor="middle" fill="#991B1B" fontSize="10">search_index_failures</text>

            {/* Box 5: Basic DB Fallback */}
            <rect x="220" y="120" width="360" height="60" rx="4" fill="#FFFFFF" stroke="#E4E4E7" strokeWidth="1.5" />
            <text x="400" y="145" textAnchor="middle" fill="#18181B" fontSize="12" fontWeight="600">Zero-Cost Fallback: GET /search/basic</text>
            <text x="400" y="162" textAnchor="middle" fill="#71717A" fontSize="10">PostgreSQL ILIKE queries scoped strictly by organization_id</text>
          </svg>
        </div>
      </div>

      {/* Technical Specifications */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-6 shadow-sm space-y-4 text-[13px] text-[#52525B] leading-relaxed">
        <h2 className="text-[14px] font-semibold text-[#18181B]">Implementation Details (Audit Section 12.2)</h2>
        <ul className="space-y-2 list-disc pl-5">
          <li>
            <strong className="text-[#18181B]">Tenant Isolation:</strong> All Meilisearch document indices (<code className="font-mono text-[#18181B]">files</code>, <code className="font-mono text-[#18181B]">members</code>, <code className="font-mono text-[#18181B]">audit_logs</code>) configure <code className="font-mono text-[#18181B]">organization_id</code> as a required filterable attribute. The search client automatically injects <code className="font-mono text-[#18181B]">filter: organization_id = &apos;...&apos;</code> into every query.
          </li>
          <li>
            <strong className="text-[#18181B]">Circuit Breaker:</strong> The Meilisearch client maintains circuit breaker states (<code className="font-mono">CLOSED</code>, <code className="font-mono">OPEN</code>, <code className="font-mono">HALF-OPEN</code>). If 5 network failures occur within a 30-second window, the circuit trips <code className="font-mono">OPEN</code> to prevent request hanging.
          </li>
          <li>
            <strong className="text-[#18181B]">Dead-Letter Persistence:</strong> When indexing jobs fail or the circuit is open, tasks record failure entries to the database table <code className="font-mono text-[#18181B]">search_index_failures</code> for subsequent replay.
          </li>
          <li>
            <strong className="text-[#18181B]">Database Fallback:</strong> The endpoint <code className="font-mono text-[#18181B]">GET /search/basic</code> queries files, memberships, and audit logs using PostgreSQL case-insensitive pattern matching, remaining functional without Meilisearch.
          </li>
        </ul>
      </div>
    </div>
  );
};
