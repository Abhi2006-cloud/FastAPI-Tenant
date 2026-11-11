import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { OrgProvider, useOrg } from "../shared/context/OrgContext.tsx";
import { getActiveOrgId } from "../shared/api/client.ts";
import { AuthProvider } from "../shared/context/AuthContext.tsx";
import { apiClient } from "../shared/api/client.ts";

vi.mock("../shared/api/client.ts", async () => {
  const actual = await vi.importActual<typeof import("../shared/api/client.ts")>("../shared/api/client.ts");
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
      post: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    },
  };
});

const DummyOrgConsumer = () => {
  const { activeOrgId, myOrgs, switchOrg } = useOrg();
  return (
    <div>
      <div data-testid="active-org">{activeOrgId}</div>
      <div data-testid="org-count">{myOrgs.length}</div>
      <button onClick={() => switchOrg("org-456")} data-testid="switch-btn">
        Switch to Org 456
      </button>
    </div>
  );
};

describe("OrgContext & Route Synchronization", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === "/auth/me") {
        return Promise.resolve({
          data: { id: "user-1", email: "user@test.com", created_at: "2026-01-01" },
        } as never);
      }
      if (url === "/organizations/my") {
        return Promise.resolve({
          data: [
            { id: "org-123", name: "Org Alpha", role: "owner" },
            { id: "org-456", name: "Org Beta", role: "member" },
          ],
        } as never);
      }
      if (url.includes("/entitlements")) {
        return Promise.resolve({
          data: {
            plan: "free",
            limits: { max_members: 5, max_files: 20, max_upload_mb: 2, org_storage_mb: 25 },
            usage: { members_count: 1, files_count: 0, storage_mb: 0, invites_used_this_hour: 0 },
            features: [],
            invites_remaining_this_hour: 10,
          },
        } as never);
      }
      return Promise.reject(new Error(`Unhandled GET ${url}`));
    });
  });

  it("synchronizes activeOrgId from URL parameter /o/:orgId", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={["/o/org-123/overview"]}>
            <Routes>
              <Route
                path="/o/:orgId/*"
                element={
                  <OrgProvider>
                    <DummyOrgConsumer />
                  </OrgProvider>
                }
              />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("active-org").textContent).toBe("org-123");
    });
    expect(getActiveOrgId()).toBe("org-123");
  });

  it("switches org and updates route parameter and activeOrgId in client", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={["/o/org-123/overview"]}>
            <Routes>
              <Route
                path="/o/:orgId/*"
                element={
                  <OrgProvider>
                    <DummyOrgConsumer />
                  </OrgProvider>
                }
              />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("active-org").textContent).toBe("org-123");
    });

    fireEvent.click(screen.getByTestId("switch-btn"));

    await waitFor(() => {
      expect(getActiveOrgId()).toBe("org-456");
    });
  });
});
