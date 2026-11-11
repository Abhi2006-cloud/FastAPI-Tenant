import React, { createContext, useContext, useState, useEffect } from "react";
import { apiClient, setAccessToken, setRefreshToken, getRefreshToken, onUnauthorized } from "../api/client.ts";
import type { UserResponse, DemoSessionResponse, DemoUpgradeResponse } from "../api/types.ts";

interface AuthContextValue {
  user: UserResponse | null;
  isLoading: boolean;
  isDemo: boolean;
  demoExpiresAt: string | null;
  login: (email: string, password: string) => Promise<UserResponse>;
  register: (email: string, password: string) => Promise<UserResponse>;
  startDemoSession: () => Promise<DemoSessionResponse>;
  upgradeDemoToPro: () => Promise<DemoUpgradeResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDemo, setIsDemo] = useState<boolean>(() => localStorage.getItem("is_demo") === "true");
  const [demoExpiresAt, setDemoExpiresAt] = useState<string | null>(() => localStorage.getItem("demo_expires_at"));

  const fetchCurrentUser = async () => {
    try {
      const res = await apiClient.get<UserResponse>("/auth/me");
      setUser(res.data);
    } catch {
      setUser(null);
      setAccessToken(null);
      setRefreshToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      // Refresh token exists in localStorage; attempt to restore session via /auth/refresh
      apiClient
        .post<{ access_token: string; refresh_token?: string }>("/auth/refresh", { refresh_token: refreshToken })
        .then((res) => {
          setAccessToken(res.data.access_token);
          if (res.data.refresh_token) {
            setRefreshToken(res.data.refresh_token);
          }
          return fetchCurrentUser();
        })
        .catch(() => {
          setAccessToken(null);
          setRefreshToken(null);
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }

    onUnauthorized(() => {
      setUser(null);
    });

    return () => {
      onUnauthorized(null);
    };
  }, []);

  const login = async (email: string, password: string): Promise<UserResponse> => {
    const res = await apiClient.post<{ access_token: string; refresh_token: string; user?: UserResponse }>(
      "/auth/login",
      { email, password }
    );
    setAccessToken(res.data.access_token);
    setRefreshToken(res.data.refresh_token);
    localStorage.removeItem("is_demo");
    localStorage.removeItem("demo_expires_at");
    setIsDemo(false);
    setDemoExpiresAt(null);
    const userRes = await apiClient.get<UserResponse>("/auth/me");
    setUser(userRes.data);
    return userRes.data;
  };

  const register = async (email: string, password: string): Promise<UserResponse> => {
    await apiClient.post("/auth/register", { email, password });
    return login(email, password);
  };

  const startDemoSession = async (): Promise<DemoSessionResponse> => {
    const res = await apiClient.post<DemoSessionResponse>("/demo/session");
    setAccessToken(res.data.access_token);
    setRefreshToken(res.data.refresh_token);
    const expires = new Date(Date.now() + res.data.expires_in * 1000).toISOString();
    localStorage.setItem("is_demo", "true");
    localStorage.setItem("demo_expires_at", expires);
    setIsDemo(true);
    setDemoExpiresAt(expires);
    const userRes = await apiClient.get<UserResponse>("/auth/me");
    setUser(userRes.data);
    return res.data;
  };

  const upgradeDemoToPro = async (): Promise<DemoUpgradeResponse> => {
    const res = await apiClient.post<DemoUpgradeResponse>("/demo/upgrade");
    await fetchCurrentUser();
    return res.data;
  };

  const logout = async () => {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) {
        await apiClient.post("/auth/logout", { refresh_token: refreshToken });
      }
    } catch {
      // Ignore network errors on logout
    } finally {
      setAccessToken(null);
      setRefreshToken(null);
      setUser(null);
      localStorage.removeItem("is_demo");
      localStorage.removeItem("demo_expires_at");
      setIsDemo(false);
      setDemoExpiresAt(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isDemo,
        demoExpiresAt,
        login,
        register,
        startDemoSession,
        upgradeDemoToPro,
        logout,
        refreshUser: fetchCurrentUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
