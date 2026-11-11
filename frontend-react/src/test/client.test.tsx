import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import {
  apiClient,
  onPlanUpgradeRequired,
  onRateLimited,
  setAccessToken,
  setRefreshToken,
  getAccessToken,
  getRefreshToken,
} from "../shared/api/client.ts";

vi.mock("axios", async () => {
  const actualAxios = await vi.importActual<typeof axios>("axios");
  return {
    ...actualAxios,
    default: {
      ...actualAxios,
      post: vi.fn(),
      create: actualAxios.create,
    },
  };
});

describe("Axios Layer Cross-Cutting Interceptors", () => {
  beforeEach(() => {
    setAccessToken(null);
    setRefreshToken(null);
    vi.clearAllMocks();
  });

  it("triggers plan upgrade listener on 402 response", async () => {
    const upgradeListener = vi.fn();
    onPlanUpgradeRequired(upgradeListener);

    // Mock a 402 rejection
    const mockError = {
      response: {
        status: 402,
        data: {
          detail: {
            code: "PLAN_FEATURE_LOCKED",
            feature: "audit_export",
            required_plan: "pro",
            current_plan: "free",
          },
        },
      },
    };

    // Test rejection handler directly via interceptor
    const responseInterceptor = (apiClient.interceptors.response as unknown as {
      handlers: Array<{ rejected: (error: unknown) => Promise<unknown> }>;
    }).handlers[0].rejected;

    await expect(responseInterceptor(mockError)).rejects.toBeDefined();
    expect(upgradeListener).toHaveBeenCalledWith({
      code: "PLAN_FEATURE_LOCKED",
      feature: "audit_export",
      required_plan: "pro",
      current_plan: "free",
    });
  });

  it("triggers rate limit listener on 429 response", async () => {
    const rateLimitListener = vi.fn();
    onRateLimited(rateLimitListener);

    const mockError = {
      response: {
        status: 429,
        headers: { "retry-after": "45" },
        data: { detail: { code: "RATE_LIMITED", retry_after: 45 } },
      },
    };

    const responseInterceptor = (apiClient.interceptors.response as unknown as {
      handlers: Array<{ rejected: (error: unknown) => Promise<unknown> }>;
    }).handlers[0].rejected;

    await expect(responseInterceptor(mockError)).rejects.toBeDefined();
    expect(rateLimitListener).toHaveBeenCalledWith(45);
  });

  it("executes single-flight refresh on 401 and updates tokens", async () => {
    setRefreshToken("initial-refresh-token");
    setAccessToken("expired-access-token");

    // Mock axios.post to simulate successful token refresh
    vi.mocked(axios.post).mockResolvedValueOnce({
      data: {
        access_token: "new-access-token",
        refresh_token: "rotated-refresh-token",
      },
    });

    const mockOriginalRequest = {
      url: "/files",
      headers: {
        set: vi.fn(),
      },
    };

    const mock401Error = {
      response: { status: 401 },
      config: mockOriginalRequest,
    };

    const responseInterceptor = (apiClient.interceptors.response as unknown as {
      handlers: Array<{ rejected: (error: unknown) => Promise<unknown> }>;
    }).handlers[0].rejected;

    // Trigger interceptor
    try {
      await responseInterceptor(mock401Error);
    } catch {
      // apiClient call mock in unit test
    }

    expect(getAccessToken()).toBe("new-access-token");
    expect(getRefreshToken()).toBe("rotated-refresh-token");
  });
});

