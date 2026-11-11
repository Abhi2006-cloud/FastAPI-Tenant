import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Server } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiClient, getActiveOrgId } from "../api/client.ts";
import type { PlatformLimitsResponse, EntitlementsResponse } from "../api/types.ts";

export interface DocsTocItem {
  id: string;
  label: string;
}

export interface DocsLayoutProps {
  title: string;
  summary: string;
  featureKey: "meilisearch_search" | "email_delivery";
  backTo?: {
    label: string;
    to: string;
  };
  tableOfContents?: DocsTocItem[];
  children: React.ReactNode;
}

export const DocsLayout: React.FC<DocsLayoutProps> = ({
  title,
  summary,
  featureKey,
  backTo,
  tableOfContents,
  children,
}) => {
  const activeOrgId = getActiveOrgId();

  // Query platform limits for infrastructure state
  const { data: platformLimits } = useQuery<PlatformLimitsResponse>({
    queryKey: ["platform-limits"],
    queryFn: async () => {
      const res = await apiClient.get<PlatformLimitsResponse>("/platform/limits");
      return res.data;
    },
    staleTime: 60_000,
  });

  // Query active org entitlements if inside an org context
  const { data: entitlements } = useQuery<EntitlementsResponse>({
    queryKey: ["entitlements", activeOrgId],
    queryFn: async () => {
      if (!activeOrgId) throw new Error("No active org");
      const res = await apiClient.get<EntitlementsResponse>(`/organizations/${activeOrgId}/entitlements`);
      return res.data;
    },
    enabled: !!activeOrgId,
    staleTime: 60_000,
  });

  // Determine dynamic status badge from features response
  const isEnabled = React.useMemo(() => {
    const services = platformLimits?.services as
      | { search?: { status?: string }; email?: { status?: string; mode?: string } }
      | undefined;

    if (featureKey === "meilisearch_search") {
      const feature = entitlements?.features?.find((f) => f.key === "meilisearch_search");
      if (feature && feature.state === "included") return true;
      return services?.search?.status === "enabled";
    }
    if (featureKey === "email_delivery") {
      const feature = entitlements?.features?.find((f) => f.key === "email_delivery");
      if (feature && feature.state === "included") return true;
      return services?.email?.status === "connected" && services?.email?.mode === "production";
    }
    return false;
  }, [featureKey, entitlements, platformLimits]);

  const badgeText = isEnabled
    ? "Active on this deployment"
    : "Paid feature, not enabled on this deployment";

  // Derive back link
  const defaultBackLink = React.useMemo(() => {
    if (featureKey === "meilisearch_search") {
      return activeOrgId
        ? { label: "Back to Workspace Search", to: `/o/${activeOrgId}/search` }
        : { label: "Back to Platform Status", to: "/platform" };
    }
    return activeOrgId
      ? { label: "Back to Team Invitations", to: `/o/${activeOrgId}/invitations` }
      : { label: "Back to Platform Status", to: "/platform" };
  }, [featureKey, activeOrgId]);

  const effectiveBackLink = backTo || defaultBackLink;

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col text-[#18181B] antialiased">
      {/* Top Header */}
      <header className="border-b border-[#E4E4E7] bg-white sticky top-0 z-30">
        <div className="max-w-[1040px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link
            to={effectiveBackLink.to}
            className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#0F766E] hover:underline"
          >
            <ArrowLeft className="w-4 h-4 shrink-0" />
            <span>{effectiveBackLink.label}</span>
          </Link>
          <Link
            to="/platform"
            className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#71717A] hover:text-[#18181B] transition-colors"
          >
            <Server className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Platform Status</span>
          </Link>
        </div>
      </header>

      {/* Main Content Container: Centered, max-w 720px reading column */}
      <div className="flex-1 w-full max-w-[1040px] mx-auto px-4 sm:px-6 py-8 sm:py-12 flex gap-12 justify-center">
        {/* Reading Column */}
        <main className="w-full max-w-[720px] shrink-0">
          {/* Page Header */}
          <header className="border-b border-[#E4E4E7] pb-6 mb-8">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-3">
              <h1 className="text-[28px] font-semibold text-[#18181B] tracking-tight leading-tight m-0">
                {title}
              </h1>
              <span
                data-testid="docs-status-badge"
                className={`self-start sm:self-auto inline-flex items-center px-2.5 py-1 text-[11px] font-medium tracking-wide rounded-[4px] shrink-0 border ${
                  isEnabled
                    ? "bg-[#F0FDF4] text-[#166534] border-[#BBF7D0]"
                    : "bg-[#FEF2F2] text-[#991B1B] border-[#FECACA]"
                }`}
              >
                {badgeText}
              </span>
            </div>
            <p className="text-[15px] text-[#52525B] leading-relaxed m-0">
              {summary}
            </p>
          </header>

          {/* Child Content Styled by .docs-content */}
          <article className="docs-content">
            {children}
          </article>
        </main>

        {/* Right Sidebar: "On this page" TOC (desktop only >=1024px) */}
        {tableOfContents && tableOfContents.length > 0 && (
          <aside className="hidden lg:block w-52 shrink-0 self-start sticky top-20">
            <nav className="border-l border-[#E4E4E7] pl-3 py-1 space-y-2">
              <div className="text-[11px] font-semibold text-[#18181B] uppercase tracking-wider mb-2">
                On this page
              </div>
              {tableOfContents.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className="block text-[13px] text-[#71717A] hover:text-[#0F766E] transition-colors leading-snug"
                >
                  {item.label}
                </a>
              ))}
            </nav>
          </aside>
        )}
      </div>
    </div>
  );
};

/**
 * DiagramContainer helper:
 * Renders SVG diagrams inside a bordered container with 100% width, auto height,
 * allowing horizontal scroll inside the container on mobile without breaking page layout.
 */
export const DiagramContainer: React.FC<{
  title?: string;
  minWidth?: number;
  children: React.ReactNode;
}> = ({ title, minWidth = 540, children }) => {
  return (
    <div className="w-full border border-[#E4E4E7] rounded-[6px] bg-white p-5 my-6 shadow-xs">
      {title && (
        <h3 className="text-[14px] font-semibold text-[#18181B] mb-3 !mt-0">
          {title}
        </h3>
      )}
      <div className="w-full overflow-x-auto border border-[#E4E4E7] rounded-[4px] bg-[#FAFAFA] p-3 sm:p-4">
        <div style={{ minWidth: `${minWidth}px` }} className="flex justify-center">
          {children}
        </div>
      </div>
    </div>
  );
};
