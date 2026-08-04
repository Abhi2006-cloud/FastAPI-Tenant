const ACCESS_TOKEN_KEY = 'fastapi_tenant_access_token';
const REFRESH_TOKEN_KEY = 'fastapi_tenant_refresh_token';
const SESSION_ID_KEY = 'fastapi_tenant_session_id';
const ACTIVE_ORG_ID_KEY = 'fastapi_tenant_active_org_id';
const THEME_KEY = 'fastapi_tenant_theme';

export const storage = {
  getAccessToken: (): string | null => localStorage.getItem(ACCESS_TOKEN_KEY),
  setAccessToken: (token: string): void => localStorage.setItem(ACCESS_TOKEN_KEY, token),
  removeAccessToken: (): void => localStorage.removeItem(ACCESS_TOKEN_KEY),

  getRefreshToken: (): string | null => localStorage.getItem(REFRESH_TOKEN_KEY),
  setRefreshToken: (token: string): void => localStorage.setItem(REFRESH_TOKEN_KEY, token),
  removeRefreshToken: (): void => localStorage.removeItem(REFRESH_TOKEN_KEY),

  getSessionId: (): string | null => localStorage.getItem(SESSION_ID_KEY),
  setSessionId: (id: string): void => localStorage.setItem(SESSION_ID_KEY, id),
  removeSessionId: (): void => localStorage.removeItem(SESSION_ID_KEY),

  getActiveOrgId: (): string | null => localStorage.getItem(ACTIVE_ORG_ID_KEY),
  setActiveOrgId: (id: string): void => localStorage.setItem(ACTIVE_ORG_ID_KEY, id),
  removeActiveOrgId: (): void => localStorage.removeItem(ACTIVE_ORG_ID_KEY),

  getTheme: (): 'light' | 'dark' | 'system' => (localStorage.getItem(THEME_KEY) as 'light' | 'dark' | 'system') || 'system',
  setTheme: (theme: 'light' | 'dark' | 'system'): void => localStorage.setItem(THEME_KEY, theme),

  clearAuth: (): void => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(SESSION_ID_KEY);
  },
};
