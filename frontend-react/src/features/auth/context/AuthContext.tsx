import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { storage } from '../../../shared/utils/storage';
import { apiClient } from '../../../shared/api/client';
import { User, UserLogin, UserRegister } from '../types';

export type AuthState =
  | 'UNKNOWN'
  | 'CHECKING_SESSION'
  | 'AUTHENTICATED'
  | 'UNAUTHENTICATED'
  | 'REFRESHING_TOKEN'
  | 'SESSION_EXPIRED'
  | 'LOGGING_OUT';

interface AuthContextType {
  authState: AuthState;
  user: User | null;
  login: (data: UserLogin) => Promise<void>;
  register: (data: UserRegister) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: (keepCurrent?: boolean) => Promise<void>;
  checkSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>('UNKNOWN');
  const [user, setUser] = useState<User | null>(null);

  const checkSession = useCallback(async () => {
    const token = storage.getAccessToken();
    if (!token) {
      setUser(null);
      setAuthState('UNAUTHENTICATED');
      return;
    }

    setAuthState('CHECKING_SESSION');
    try {
      const response = await apiClient.get('/auth/me');
      setUser(response.data);
      setAuthState('AUTHENTICATED');
    } catch {
      setUser(null);
      setAuthState('UNAUTHENTICATED');
    }
  }, []);

  useEffect(() => {
    checkSession();

    const handleSessionExpired = () => {
      setUser(null);
      setAuthState('SESSION_EXPIRED');
    };

    window.addEventListener('auth:session_expired', handleSessionExpired);
    return () => {
      window.removeEventListener('auth:session_expired', handleSessionExpired);
    };
  }, [checkSession]);

  const login = async (data: UserLogin) => {
    setAuthState('CHECKING_SESSION');
    try {
      const response = await apiClient.post('/auth/login', data);
      const { access_token, refresh_token, session_id } = response.data;

      storage.setAccessToken(access_token);
      storage.setRefreshToken(refresh_token);
      if (session_id) {
        storage.setSessionId(session_id);
      }

      await checkSession();
    } catch (error) {
      setAuthState('UNAUTHENTICATED');
      throw error;
    }
  };

  const register = async (data: UserRegister) => {
    await apiClient.post('/auth/register', data);
    // Automatically log in after registration
    await login({ email: data.email, password: data.password });
  };

  const logout = async () => {
    setAuthState('LOGGING_OUT');
    const refreshToken = storage.getRefreshToken();
    try {
      if (refreshToken) {
        await apiClient.post('/auth/logout', { refresh_token: refreshToken });
      }
    } catch {
      // Ignore network errors during logout
    } finally {
      storage.clearAuth();
      setUser(null);
      setAuthState('UNAUTHENTICATED');
    }
  };

  const logoutAll = async (keepCurrent: boolean = false) => {
    setAuthState('LOGGING_OUT');
    const refreshToken = storage.getRefreshToken();
    try {
      await apiClient.post('/auth/logout-all', {
        refresh_token: refreshToken,
        keep_current: keepCurrent,
      });
    } finally {
      if (!keepCurrent) {
        storage.clearAuth();
        setUser(null);
        setAuthState('UNAUTHENTICATED');
      } else {
        await checkSession();
      }
    }
  };

  return (
    <AuthContext.Provider
      value={{
        authState,
        user,
        login,
        register,
        logout,
        logoutAll,
        checkSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
