import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FeatureGate } from "../shared/components/FeatureGate.tsx";
import * as client from "../shared/api/client.ts";

vi.mock("../shared/api/client.ts", async (importOriginal) => {
  const actual = await importOriginal<typeof client>();
  return {
    ...actual,
    getActiveOrgId: vi.fn().mockReturnValue("org-123"),
    apiClient: {
      get: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    },
  };
});

function renderWithProviders(ui: React.ReactElement, mockEntitlements: unknown) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  // Pre-seed query cache for entitlements
  queryClient.setQueryData(["entitlements", "org-123"], mockEntitlements);

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe("FeatureGate Component (4 States)", () => {
  it("renders children normally when feature is 'included'", () => {
    const mockEntitlements = {
      plan: "pro",
      features: [{ key: "audit_export", label: "Audit Log Export", state: "included" }],
    };

    renderWithProviders(
      <FeatureGate feature="audit_export">
        <button type="button">Export Button</button>
      </FeatureGate>,
      mockEntitlements
    );

    expect(screen.getByText("Export Button")).toBeInTheDocument();
    expect(screen.queryByText("Pro")).not.toBeInTheDocument();
  });

  it("renders disabled control with Pro badge when feature is 'plan_locked'", () => {
    const mockEntitlements = {
      plan: "free",
      features: [{ key: "audit_export", label: "Audit Log Export", state: "plan_locked" }],
    };

    renderWithProviders(
      <FeatureGate feature="audit_export">
        <button type="button">Export Button</button>
      </FeatureGate>,
      mockEntitlements
    );

    expect(screen.getByText("Export Button")).toBeInTheDocument();
    expect(screen.getByText("Pro")).toBeInTheDocument();
  });

  it("renders 'Not available on this deployment' banner when feature is 'deployment_disabled'", () => {
    const mockEntitlements = {
      plan: "free",
      features: [{ key: "instant_search", label: "Search", state: "deployment_disabled" }],
    };

    renderWithProviders(
      <FeatureGate feature="instant_search">
        <input placeholder="Search" />
      </FeatureGate>,
      mockEntitlements
    );

    expect(screen.getByText(/Not available on this deployment/i)).toBeInTheDocument();
    expect(screen.getByText(/View architecture docs/i)).toBeInTheDocument();
  });

  it("renders 'Coming soon' badge when feature is 'coming_soon'", () => {
    const mockEntitlements = {
      plan: "free",
      features: [{ key: "sso_saml", label: "SSO", state: "coming_soon" }],
    };

    renderWithProviders(
      <FeatureGate feature="sso_saml">
        <button type="button">SSO Login</button>
      </FeatureGate>,
      mockEntitlements
    );

    expect(screen.getByText(/Coming soon/i)).toBeInTheDocument();
  });
});
