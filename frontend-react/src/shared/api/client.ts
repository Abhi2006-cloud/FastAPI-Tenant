import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import type { PlanUpgradeErrorData } from "./types.ts";

let inMemoryAccessToken: string | null = null;
let activeOrgId: string | null = null;

const REFRESH_TOKEN_KEY = "saas_refresh_token";

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function setActiveOrgId(orgId: string | null): void {
  activeOrgId = orgId;
}

export function getActiveOrgId(): string | null {
  return activeOrgId;
}

// Global Event listeners for Cross-Cutting Layer
type UpgradeListener = (data: PlanUpgradeErrorData) => void;
type RateLimitListener = (retryAfter: number) => void;
type AuthListener = () => void;

let upgradeListener: UpgradeListener | null = null;
let rateLimitListener: RateLimitListener | null = null;
let authListener: AuthListener | null = null;

export function onPlanUpgradeRequired(fn: UpgradeListener | null): void {
  upgradeListener = fn;
}

export function onRateLimited(fn: RateLimitListener | null): void {
  rateLimitListener = fn;
}

export function onUnauthorized(fn: AuthListener | null): void {
  authListener = fn;
}

const apiBaseUrl = (import.meta as unknown as { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    "Content-Type": "application/json",
  },
});

// Single-flight refresh token queue
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
}

// Request Interceptor: Attach Auth & X-Organization-Id
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (inMemoryAccessToken) {
    config.headers.set("Authorization", `Bearer ${inMemoryAccessToken}`);
  }
  if (activeOrgId && !config.headers.has("X-Organization-Id")) {
    config.headers.set("X-Organization-Id", activeOrgId);
  }
  return config;
});

// Response Interceptor: 401 Single-Flight Refresh, 402 Upgrade, 429 Rate Limit
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // 402 Payment Required: Plan feature locked or limit reached
    if (error.response?.status === 402) {
      const data = error.response.data as { detail?: PlanUpgradeErrorData } | PlanUpgradeErrorData;
      const upgradeData = (data && "detail" in data ? data.detail : data) as PlanUpgradeErrorData;
      if (upgradeData && upgradeListener) {
        upgradeListener(upgradeData);
      }
      return Promise.reject(error);
    }

    // 429 Too Many Requests: Rate Limited
    if (error.response?.status === 429) {
      const retryAfterHeader = error.response.headers["retry-after"];
      const detail = error.response.data as { detail?: { retry_after?: number } };
      const retryAfter = detail?.detail?.retry_after ?? (retryAfterHeader ? parseInt(retryAfterHeader, 10) : 60);
      if (rateLimitListener) {
        rateLimitListener(retryAfter);
      }
      return Promise.reject(error);
    }

    // 401 Unauthorized: Attempt Single-Flight Token Refresh
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      // If the failed request was itself the refresh endpoint, don't loop
      if (originalRequest.url?.includes("/auth/refresh") || originalRequest.url?.includes("/auth/login")) {
        setAccessToken(null);
        setRefreshToken(null);
        if (authListener) authListener();
        return Promise.reject(error);
      }

      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        setAccessToken(null);
        if (authListener) authListener();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.set("Authorization", `Bearer ${token}`);
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const res = await axios.post<{ access_token: string; refresh_token?: string }>(
          `${apiBaseUrl}/auth/refresh`,
          { refresh_token: refreshToken },
          { headers: { "Content-Type": "application/json" } }
        );

        const newAccessToken = res.data.access_token;
        setAccessToken(newAccessToken);
        if (res.data.refresh_token) {
          setRefreshToken(res.data.refresh_token);
        }

        processQueue(null, newAccessToken);

        originalRequest.headers.set("Authorization", `Bearer ${newAccessToken}`);
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        setAccessToken(null);
        setRefreshToken(null);
        if (authListener) authListener();
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

