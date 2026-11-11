/**
 * Endpoints used by this page:
 * - GET /platform/limits
 * - GET /health
 * - GET /jobs
 * - GET /email/logs
 * - GET /email/stats
 */
import React, { useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { useQuery } from "@tanstack/react-query";
import { Server, Activity, Mail, RefreshCw } from "lucide-react";
import { apiClient } from "../../shared/api/client.ts";
import type { PlatformLimitsResponse } from "../../shared/api/types.ts";

interface HealthResponse {
  status: string;
  version: string;
  database: string;
  redis: string;
  search: string;
  session_store: string;
  email: string;
  worker?: {
    mode: string;
    alive: boolean;
    status: string;
  };
  queues?: Record<string, { queued: number; finished: number; failed: number }>;
}

interface PlatformLimitsDetail {
  deployment?: {
    environment?: string;
    tier?: string;
    storage_backend?: string;
    worker_mode?: string;
  };
  compute_provider?: {
    name?: string;
    memory_mb?: number;
    cpu?: string;
    ephemeral_disk?: boolean;
    idle_sleep_minutes?: number;
    cold_start_seconds?: string;
    single_service?: boolean;
  };
  database_provider?: {
    name?: string;
    storage_gb?: number;
    pooled_connection?: boolean;
    auto_suspend?: boolean;
  };
  redis_provider?: {
    name?: string;
    protocol?: string;
    max_commands_per_second?: number;
    max_record_size_mb?: number;
    max_data_size_mb?: number;
    monthly_bandwidth_gb?: number;
  };
  services?: {
    search?: {
      provider?: string;
      status?: string;
      available?: boolean;
    };
    email?: {
      provider?: string;
      mode?: string;
    };
  };
}

export const PlatformPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState("platform");

  // Query platform limits
  const { data: limitsData, isLoading: limitsLoading, refetch: refetchLimits } = useQuery<PlatformLimitsResponse>({
    queryKey: ["platform-limits"],
    queryFn: async () => {
      const res = await apiClient.get<PlatformLimitsResponse>("/platform/limits");
      return res.data;
    },
  });

  const pData = (limitsData || {}) as unknown as PlatformLimitsDetail;

  // Query health endpoint
  const { data: healthData, isLoading: healthLoading, refetch: refetchHealth } = useQuery<HealthResponse>({
    queryKey: ["platform-health"],
    queryFn: async () => {
      const res = await apiClient.get<HealthResponse>("/health");
      return res.data;
    },
    refetchInterval: 15_000,
  });

  // Query admin jobs (will fail gracefully with 403 if user is not platform admin)
  const { data: jobsData } = useQuery({
    queryKey: ["admin-jobs"],
    queryFn: async () => {
      const res = await apiClient.get("/jobs");
      return res.data;
    },
    retry: false,
  });

  // Query admin email stats (will fail gracefully with 403 if user is not owner/admin)
  const { data: emailStats } = useQuery({
    queryKey: ["admin-email-stats"],
    queryFn: async () => {
      const res = await apiClient.get("/email/stats");
      return res.data;
    },
    retry: false,
  });

  const isPlatformAdmin = !!jobsData;

  const handleRefresh = () => {
    refetchLimits();
    refetchHealth();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-semibold text-[#18181B] tracking-tight">Platform & Infrastructure</h1>
          <p className="text-[13px] text-[#71717A] mt-0.5">
            Zero-cost runtime metrics, provider limits, and system health status.
          </p>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-[#E4E4E7] text-[12px] font-medium rounded-[6px] hover:bg-white transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5 text-[#71717A]" />
          <span>Refresh Metrics</span>
        </button>
      </div>

      <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
        <Tabs.List className="flex border-b border-[#E4E4E7] space-x-4 mb-4">
          <Tabs.Trigger
            value="platform"
            className="pb-2 text-[13px] font-medium text-[#71717A] data-[state=active]:text-[#0F766E] data-[state=active]:border-b-2 data-[state=active]:border-[#0F766E] focus:outline-none"
          >
            How this runs for free
          </Tabs.Trigger>
          <Tabs.Trigger
            value="health"
            className="pb-2 text-[13px] font-medium text-[#71717A] data-[state=active]:text-[#0F766E] data-[state=active]:border-b-2 data-[state=active]:border-[#0F766E] focus:outline-none"
          >
            Live Health & Queues
          </Tabs.Trigger>
          {isPlatformAdmin && (
            <Tabs.Trigger
              value="admin"
              className="pb-2 text-[13px] font-medium text-[#71717A] data-[state=active]:text-[#0F766E] data-[state=active]:border-b-2 data-[state=active]:border-[#0F766E] focus:outline-none"
            >
              Platform Admin (G9)
            </Tabs.Trigger>
          )}
        </Tabs.List>

        {/* Tab 1: How this runs for free */}
        <Tabs.Content value="platform" className="space-y-6 focus:outline-none">
          <div className="bg-white border border-[#E4E4E7] rounded-[6px] overflow-hidden shadow-sm">
            <div className="px-4 py-3 bg-[#FAFAFA] border-b border-[#E4E4E7] flex items-center gap-2">
              <Server className="w-4 h-4 text-[#0F766E]" />
              <h2 className="text-[13px] font-semibold text-[#18181B]">Zero-Cost Provider Constraints</h2>
            </div>

            {limitsLoading || !limitsData ? (
              <div className="p-6 text-center text-[#71717A] text-[13px]">Loading provider metrics...</div>
            ) : (
              <table className="w-full text-left border-collapse text-[13px]">
                <thead>
                  <tr className="border-b border-[#E4E4E7] text-[11px] font-semibold text-[#71717A] uppercase bg-[#FAFAFA]">
                    <th className="py-2 px-4">Provider / Layer</th>
                    <th className="py-2 px-4">Tier / Metric</th>
                    <th className="py-2 px-4">Limit / Design Choice</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7]">
                  <tr>
                    <td className="py-3 px-4 font-medium text-[#18181B]">{pData.compute_provider?.name || "Render Free Web Service"}</td>
                    <td className="py-3 px-4 text-[#52525B]">Memory & Lifecycle</td>
                    <td className="py-3 px-4 tabular-nums">
                      {pData.compute_provider?.memory_mb || 512} MB RAM • Shared CPU • Spin-down after {pData.compute_provider?.idle_sleep_minutes || 15}m idle • Ephemeral disk
                    </td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-medium text-[#18181B]">{pData.database_provider?.name || "Neon PostgreSQL"}</td>
                    <td className="py-3 px-4 text-[#52525B]">Storage & Pooler</td>
                    <td className="py-3 px-4 tabular-nums">
                      {pData.database_provider?.storage_gb ? `${pData.database_provider.storage_gb * 1024} MB Max Storage` : "—"} • PgBouncer Pooler • Autosuspends
                    </td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-medium text-[#18181B]">{pData.redis_provider?.name || "Upstash Redis"}</td>
                    <td className="py-3 px-4 text-[#52525B]">Commands & Size</td>
                    <td className="py-3 px-4 tabular-nums">
                      {pData.redis_provider?.max_commands_per_second ? `${pData.redis_provider.max_commands_per_second.toLocaleString()} cmd/s` : "10,000 cmd/s"} • {pData.redis_provider?.max_data_size_mb || 250} MB max data • TLS {pData.redis_provider?.protocol || "rediss"}://
                    </td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-medium text-[#18181B]">File Storage Strategy</td>
                    <td className="py-3 px-4 text-[#52525B]">Backend Mode</td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-[12px] bg-[#F4F4F5] px-1.5 py-0.5 rounded text-[#0F766E]">
                        {pData.deployment?.storage_backend || "database"}
                      </span>{" "}
                      (Survives Render container restarts)
                    </td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-medium text-[#18181B]">Background Jobs</td>
                    <td className="py-3 px-4 text-[#52525B]">Worker Process</td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-[12px] bg-[#F4F4F5] px-1.5 py-0.5 rounded text-[#0F766E]">
                        {pData.deployment?.worker_mode || "embedded"}
                      </span>{" "}
                      (Embedded thread pool inside web service)
                    </td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-medium text-[#18181B]">Search & Email Services</td>
                    <td className="py-3 px-4 text-[#52525B]">Feature Flags</td>
                    <td className="py-3 px-4 text-[#71717A]">
                      Search: <span className="font-semibold text-[#18181B]">{pData.services?.search?.status || "disabled"}</span> • Email: <span className="font-semibold text-[#18181B]">{pData.services?.email?.mode || "console"}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            )}
          </div>
        </Tabs.Content>

        {/* Tab 2: Live Health & Queues */}
        <Tabs.Content value="health" className="space-y-6 focus:outline-none">
          <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 pb-2 border-b border-[#E4E4E7]">
              <Activity className="w-4 h-4 text-[#0F766E]" />
              <h2 className="text-[13px] font-semibold text-[#18181B]">Live Service Health (/health)</h2>
            </div>

            {healthLoading || !healthData ? (
              <div className="text-center text-[#71717A] py-6 text-[13px]">Checking live service health...</div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-3 bg-[#FAFAFA] border border-[#E4E4E7] rounded-[6px]">
                  <span className="text-[11px] text-[#71717A] uppercase font-semibold">PostgreSQL</span>
                  <div className="text-[14px] font-medium text-[#18181B] mt-1 capitalize">{healthData.database}</div>
                </div>
                <div className="p-3 bg-[#FAFAFA] border border-[#E4E4E7] rounded-[6px]">
                  <span className="text-[11px] text-[#71717A] uppercase font-semibold">Redis</span>
                  <div className="text-[14px] font-medium text-[#18181B] mt-1 capitalize">{healthData.redis}</div>
                </div>
                <div className="p-3 bg-[#FAFAFA] border border-[#E4E4E7] rounded-[6px]">
                  <span className="text-[11px] text-[#71717A] uppercase font-semibold">Sessions</span>
                  <div className="text-[14px] font-medium text-[#18181B] mt-1 capitalize">{healthData.session_store}</div>
                </div>
                <div className="p-3 bg-[#FAFAFA] border border-[#E4E4E7] rounded-[6px]">
                  <span className="text-[11px] text-[#71717A] uppercase font-semibold">Worker Thread</span>
                  <div className="text-[14px] font-medium text-[#18181B] mt-1 capitalize">{healthData.worker?.mode || "embedded"}</div>
                </div>
              </div>
            )}

            {healthData?.queues && (
              <div className="pt-4 border-t border-[#E4E4E7]">
                <h3 className="text-[12px] font-semibold text-[#71717A] uppercase mb-3">RQ Background Queue Depths</h3>
                <div className="grid grid-cols-3 gap-4">
                  {Object.entries(healthData.queues).map(([name, q]) => (
                    <div key={name} className="p-3 bg-white border border-[#E4E4E7] rounded-[6px] text-[12px]">
                      <span className="font-semibold text-[#18181B] capitalize">{name} Queue</span>
                      <div className="mt-1 text-[#52525B] tabular-nums">
                        Queued: <span className="font-medium text-[#18181B]">{q.queued}</span> • Finished: {q.finished} • Failed: {q.failed}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Tabs.Content>

        {/* Tab 3: Admin Only (Jobs & Email Logs) */}
        {isPlatformAdmin && (
          <Tabs.Content value="admin" className="space-y-6 focus:outline-none">
            <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-5 space-y-4 shadow-sm">
              <div className="flex items-center gap-2 pb-2 border-b border-[#E4E4E7]">
                <Mail className="w-4 h-4 text-[#0F766E]" />
                <h2 className="text-[13px] font-semibold text-[#18181B]">Platform Admin Monitoring (G9 Endpoints)</h2>
              </div>

              {emailStats && (
                <div className="p-4 bg-[#FAFAFA] border border-[#E4E4E7] rounded-[6px] space-y-2 text-[13px]">
                  <span className="text-[12px] font-semibold text-[#18181B]">Email Infrastructure Stats</span>
                  <div className="grid grid-cols-3 gap-4 tabular-nums">
                    <div>Total Sent: {emailStats.total_emails || 0}</div>
                    <div>Success Rate: {emailStats.success_rate_percent || 0}%</div>
                    <div>Provider: {emailStats.active_provider || "console"}</div>
                  </div>
                </div>
              )}

              <div>
                <span className="text-[12px] font-semibold text-[#18181B] block mb-2">Raw Background Job Status</span>
                <pre className="text-[11px] p-3 bg-[#F4F4F5] rounded text-[#18181B] overflow-x-auto font-mono">
                  {JSON.stringify(jobsData, null, 2)}
                </pre>
              </div>
            </div>
          </Tabs.Content>
        )}
      </Tabs.Root>
    </div>
  );
};
