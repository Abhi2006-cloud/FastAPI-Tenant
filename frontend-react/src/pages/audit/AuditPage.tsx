/**
 * Endpoints used by this page:
 * - GET /audit-logs
 * - GET /audit-logs/export
 */
import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, ChevronRight, X, ChevronLeft } from "lucide-react";
import { apiClient, getActiveOrgId } from "../../shared/api/client.ts";
import type { AuditLogListResponse, AuditLogResponse } from "../../shared/api/types.ts";
import { FeatureGate } from "../../shared/components/FeatureGate.tsx";
import { useToast } from "../../shared/components/Toast.tsx";

export const AuditPage: React.FC = () => {
  const orgId = getActiveOrgId();
  const { showToast } = useToast();

  const [page, setPage] = useState(1);
  const [selectedAction, setSelectedAction] = useState<string>("");
  const [resourceType, setResourceType] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [drawerEvent, setDrawerEvent] = useState<AuditLogResponse | null>(null);

  const { data, isLoading } = useQuery<AuditLogListResponse>({
    queryKey: ["audit-logs", orgId, page, selectedAction, resourceType, startDate, endDate],
    queryFn: async () => {
      if (!orgId) throw new Error("No active org");
      const params: Record<string, unknown> = {
        page,
        page_size: 15,
      };
      if (selectedAction) params.action = selectedAction;
      if (resourceType) params.resource_type = resourceType;
      if (startDate) params.start_date = new Date(startDate).toISOString();
      if (endDate) params.end_date = new Date(endDate).toISOString();

      const res = await apiClient.get<AuditLogListResponse>("/audit-logs", { params });
      return res.data;
    },
    enabled: !!orgId,
  });

  const handleExportCsv = async () => {
    if (!orgId) return;
    try {
      const res = await apiClient.get("/audit-logs/export", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "text/csv" }));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `audit-logs-${orgId}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      showToast("Audit logs exported to CSV.", "success");
    } catch {
      showToast("Export failed.", "error");
    }
  };

  const logs = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 15) || 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Audit Logs</h1>
          <p className="text-[13px] text-[#71717A] mt-0.5">
            Immutable compliance record of all actions taken in this workspace.
          </p>
        </div>

        {/* FeatureGate wrapped CSV Export */}
        <FeatureGate feature="audit_export">
          <button
            type="button"
            onClick={handleExportCsv}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#0F766E] hover:bg-[#115E59] text-white text-[12px] font-medium rounded-[6px] transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </FeatureGate>
      </div>

      {/* Filters Bar */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-4 flex flex-wrap gap-3 items-center text-[13px]">
        <div>
          <label htmlFor="action-filter" className="block text-[11px] font-medium text-[#71717A] mb-1">Action</label>
          <input
            id="action-filter"
            type="text"
            placeholder="e.g. PLAN_CHANGED"
            value={selectedAction}
            onChange={(e) => {
              setSelectedAction(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1 border border-[#E4E4E7] rounded-[4px] text-[12px] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
          />
        </div>

        <div>
          <label htmlFor="resource-filter" className="block text-[11px] font-medium text-[#71717A] mb-1">Resource</label>
          <input
            id="resource-filter"
            type="text"
            placeholder="e.g. organization"
            value={resourceType}
            onChange={(e) => {
              setResourceType(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1 border border-[#E4E4E7] rounded-[4px] text-[12px] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
          />
        </div>

        {/* Date Range wrapped in FeatureGate("advanced_audit_filters") */}
        <FeatureGate feature="advanced_audit_filters">
          <div className="flex gap-2">
            <div>
              <label htmlFor="start-date" className="block text-[11px] font-medium text-[#71717A] mb-1">Start Date</label>
              <input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  setPage(1);
                }}
                className="px-2 py-1 border border-[#E4E4E7] rounded-[4px] text-[12px] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
              />
            </div>
            <div>
              <label htmlFor="end-date" className="block text-[11px] font-medium text-[#71717A] mb-1">End Date</label>
              <input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value);
                  setPage(1);
                }}
                className="px-2 py-1 border border-[#E4E4E7] rounded-[4px] text-[12px] focus:outline-none focus:ring-1 focus:ring-[#0F766E]"
              />
            </div>
          </div>
        </FeatureGate>
      </div>

      {/* Logs Table */}
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#E4E4E7] bg-[#FAFAFA] text-[12px] font-semibold text-[#71717A]">
              <th className="py-2.5 px-4">Action</th>
              <th className="py-2.5 px-4">Resource</th>
              <th className="py-2.5 px-4">Timestamp</th>
              <th className="py-2.5 px-4 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E4E4E7] text-[13px]">
            {isLoading ? (
              [1, 2, 3].map((i) => (
                <tr key={i}>
                  <td colSpan={4} className="py-3 px-4">
                    <div className="h-4 bg-[#E4E4E7]/60 rounded animate-pulse w-48" />
                  </td>
                </tr>
              ))
            ) : logs.length > 0 ? (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-[#FAFAFA] transition-colors">
                  <td className="py-2.5 px-4 font-mono text-[12px] text-[#18181B] font-medium">
                    {log.action}
                  </td>
                  <td className="py-2.5 px-4 text-[#52525B] text-[12px] capitalize">
                    {log.resource_type}
                  </td>
                  <td className="py-2.5 px-4 text-[#71717A] tabular-nums text-[12px]">
                    {log.created_at ? new Date(log.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    <button
                      type="button"
                      onClick={() => setDrawerEvent(log)}
                      className="inline-flex items-center gap-1 text-[12px] text-[#0F766E] hover:underline"
                    >
                      <span>View</span>
                      <ChevronRight className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="py-8 text-center text-[#71717A]">
                  No audit logs match your query.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Pagination Controls */}
        <div className="px-4 py-3 border-t border-[#E4E4E7] bg-[#FAFAFA] flex items-center justify-between text-[12px] text-[#71717A]">
          <span>
            Showing {logs.length} of {total} events
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="p-1 border border-[#E4E4E7] rounded disabled:opacity-40 hover:bg-white"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="tabular-nums">
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="p-1 border border-[#E4E4E7] rounded disabled:opacity-40 hover:bg-white"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* JSON Metadata Drawer */}
      {drawerEvent && (
        <div className="fixed inset-0 bg-black/30 z-50 flex justify-end">
          <div className="w-full max-w-md bg-white h-full shadow-xl p-6 overflow-y-auto space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#E4E4E7]">
              <h2 className="text-[14px] font-semibold text-[#18181B]">Event Metadata</h2>
              <button
                type="button"
                onClick={() => setDrawerEvent(null)}
                className="p-1 hover:bg-[#F4F4F5] rounded text-[#71717A]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-[13px]">
              <div>
                <span className="text-[11px] text-[#71717A] uppercase font-semibold">Event ID</span>
                <div className="font-mono text-[12px] text-[#18181B] break-all">{drawerEvent.id}</div>
              </div>
              <div>
                <span className="text-[11px] text-[#71717A] uppercase font-semibold">Action</span>
                <div className="font-mono text-[12px] text-[#0F766E]">{drawerEvent.action}</div>
              </div>
              <div>
                <span className="text-[11px] text-[#71717A] uppercase font-semibold">Resource</span>
                <div className="text-[12px] text-[#18181B]">{drawerEvent.resource_type} ({drawerEvent.resource_id || "null"})</div>
              </div>
              <div>
                <span className="text-[11px] text-[#71717A] uppercase font-semibold">Actor User ID</span>
                <div className="font-mono text-[12px] text-[#18181B]">{drawerEvent.actor_user_id || "system"}</div>
              </div>
              <div>
                <span className="text-[11px] text-[#71717A] uppercase font-semibold">Timestamp</span>
                <div className="text-[12px] text-[#18181B]">{drawerEvent.created_at ? new Date(drawerEvent.created_at).toISOString() : "—"}</div>
              </div>
              <div>
                <span className="text-[11px] text-[#71717A] uppercase font-semibold">Payload</span>
                <pre className="text-[11px] p-3 bg-[#F4F4F5] rounded text-[#18181B] overflow-x-auto font-mono mt-1">
                  {JSON.stringify(drawerEvent.metadata || {}, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
