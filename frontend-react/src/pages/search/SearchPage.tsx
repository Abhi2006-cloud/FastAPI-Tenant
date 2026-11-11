/**
 * Endpoints used by this page:
 * - GET /search/basic
 */
import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Search as SearchIcon, FileText, Users, Shield, Info, ArrowUpRight } from "lucide-react";
import { apiClient, getActiveOrgId } from "../../shared/api/client.ts";
import type { GlobalSearchResponse } from "../../shared/api/types.ts";

export const SearchPage: React.FC = () => {
  const orgId = getActiveOrgId();
  const [searchTerm, setSearchTerm] = useState("");
  const [results, setResults] = useState<GlobalSearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim() || !orgId) return;

    setSearching(true);
    setHasSearched(true);
    try {
      const res = await apiClient.get<GlobalSearchResponse>("/search/basic", {
        params: { q: searchTerm.trim(), limit: 10, offset: 0 },
      });
      setResults(res.data);
    } catch {
      setResults(null);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Search</h1>
        <p className="text-[13px] text-[#71717A] mt-0.5">
          Tenant-isolated search across files, members, and audit logs.
        </p>
      </div>

      {/* Basic Search Input */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="w-4 h-4 text-[#71717A] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            required
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search files, team members, or audit action types..."
            className="w-full text-[13px] pl-9 pr-3 py-2 border border-[#E4E4E7] rounded-[6px] focus:outline-none focus:ring-1 focus:ring-[#0F766E] bg-white"
          />
        </div>
        <button
          type="submit"
          disabled={searching || !searchTerm.trim()}
          className="px-4 py-2 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] disabled:opacity-50 transition-colors"
        >
          {searching ? "Searching..." : "Search"}
        </button>
      </form>

      {/* Results Area */}
      {hasSearched && results && (
        <div className="space-y-4">
          <div className="text-[12px] text-[#71717A]">
            Found {results.totals.total} results for "{results.query}"
          </div>

          {/* Files Results */}
          <div className="bg-white border border-[#E4E4E7] rounded-[6px] overflow-hidden">
            <div className="px-4 py-2.5 bg-[#FAFAFA] border-b border-[#E4E4E7] flex items-center gap-2 text-[12px] font-semibold text-[#71717A]">
              <FileText className="w-3.5 h-3.5" />
              <span>Files ({results.totals.files})</span>
            </div>
            <div className="divide-y divide-[#E4E4E7]">
              {results.files.length > 0 ? (
                results.files.map((file, idx) => (
                  <div key={idx} className="p-3 text-[13px] flex items-center justify-between">
                    <span className="font-medium text-[#18181B]">{String(file.file_name || file.id)}</span>
                    <span className="text-[12px] text-[#71717A]">
                      {file.file_size ? `${(Number(file.file_size) / (1024 * 1024)).toFixed(2)} MB` : ""}
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-4 text-[12px] text-[#71717A]">No matching files.</div>
              )}
            </div>
          </div>

          {/* Members Results */}
          <div className="bg-white border border-[#E4E4E7] rounded-[6px] overflow-hidden">
            <div className="px-4 py-2.5 bg-[#FAFAFA] border-b border-[#E4E4E7] flex items-center gap-2 text-[12px] font-semibold text-[#71717A]">
              <Users className="w-3.5 h-3.5" />
              <span>Members ({results.totals.members})</span>
            </div>
            <div className="divide-y divide-[#E4E4E7]">
              {results.members.length > 0 ? (
                results.members.map((member, idx) => (
                  <div key={idx} className="p-3 text-[13px] flex items-center justify-between">
                    <span className="font-medium text-[#18181B]">{String(member.email || member.id)}</span>
                    <span className="text-[11px] px-2 py-0.5 bg-[#F4F4F5] rounded text-[#52525B] capitalize">
                      {String(member.role || "member")}
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-4 text-[12px] text-[#71717A]">No matching members.</div>
              )}
            </div>
          </div>

          {/* Audit Logs Results */}
          <div className="bg-white border border-[#E4E4E7] rounded-[6px] overflow-hidden">
            <div className="px-4 py-2.5 bg-[#FAFAFA] border-b border-[#E4E4E7] flex items-center gap-2 text-[12px] font-semibold text-[#71717A]">
              <Shield className="w-3.5 h-3.5" />
              <span>Audit Logs ({results.totals.audit_logs})</span>
            </div>
            <div className="divide-y divide-[#E4E4E7]">
              {results.audit_logs.length > 0 ? (
                results.audit_logs.map((log, idx) => (
                  <div key={idx} className="p-3 text-[13px] flex items-center justify-between">
                    <span className="font-mono text-[12px] text-[#18181B]">{String(log.action || log.id)}</span>
                    <span className="text-[12px] text-[#71717A] capitalize">{String(log.resource_type || "")}</span>
                  </div>
                ))
              ) : (
                <div className="p-4 text-[12px] text-[#71717A]">No matching audit logs.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Deployment Disabled Meilisearch Card */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-5 space-y-2 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-[13px] font-semibold text-[#18181B]">
            <Info className="w-4 h-4 text-[#A1A1AA]" />
            <span>Instant Typo-Tolerant Search (Meilisearch)</span>
          </div>
          <span className="px-2 py-0.5 text-[11px] font-medium tracking-wide bg-[#F4F4F5] text-[#71717A] border border-[#E4E4E7] rounded-[4px]">
            Not available on this deployment
          </span>
        </div>
        <p className="text-[12px] text-[#52525B] leading-relaxed">
          Full-text index synchronization and typo tolerance require a dedicated Meilisearch cluster. This deployment operates in zero-cost mode using PostgreSQL ILIKE basic search.
        </p>
        <div className="pt-2">
          <Link
            to="/docs/search"
            className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#0F766E] hover:underline"
          >
            <span>Learn how Meilisearch integration is architected</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
};

