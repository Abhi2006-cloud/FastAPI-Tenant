import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AcceptInvitePage } from "../pages/invitations/AcceptInvitePage.tsx";
import { ToastProvider } from "../shared/components/Toast.tsx";
import { apiClient } from "../shared/api/client.ts";
import * as AuthContextModule from "../shared/context/AuthContext.tsx";
import * as OrgContextModule from "../shared/context/OrgContext.tsx";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const mockUser = {
  id: "user-123",
  email: "member@example.com",
  created_at: new Date().toISOString(),
};

describe("AcceptInvitePage", () => {
  beforeEach(() => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: mockUser,
      isLoading: false,
      isDemo: false,
      demoExpiresAt: null,
      login: vi.fn(),
      register: vi.fn(),
      startDemoSession: vi.fn(),
      upgradeDemoToPro: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(OrgContextModule, "useOrg").mockReturnValue({
      activeOrgId: "org-1",
      activeOrg: null,
      myOrgs: [],
      entitlements: null,
      role: "member",
      isLoading: false,
      refetchOrgs: vi.fn(),
      switchOrg: vi.fn(),
    });
  });

  it("renders accept invitation form for authenticated user and extracts query token", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/invitations?token=test-token-123"]}>
          <ToastProvider>
            <AcceptInvitePage />
          </ToastProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText("Join Workspace")).toBeDefined();
    expect(screen.getByText("member@example.com")).toBeDefined();
    const input = screen.getByPlaceholderText(/Paste the invitation token/) as HTMLInputElement;
    expect(input.value).toBe("test-token-123");
    expect(screen.getByRole("button", { name: /Accept & Join/i })).toBeDefined();
  });

  it("submits token cleanly to /invitations/accept", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: {
        id: "invite-1",
        email: "member@example.com",
        organization_id: "org-456",
        status: "accepted",
        delivery_mode: "development",
        delivery_status: "accepted",
        expires_at: new Date().toISOString(),
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/invitations"]}>
          <ToastProvider>
            <AcceptInvitePage />
          </ToastProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );

    const input = screen.getByPlaceholderText(/Paste the invitation token/);
    fireEvent.change(input, { target: { value: "my-secret-invite-token" } });

    const btn = screen.getByRole("button", { name: /Accept & Join/i });
    fireEvent.click(btn);

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith("/invitations/accept", {
        token: "my-secret-invite-token",
      });
    });
  });
});