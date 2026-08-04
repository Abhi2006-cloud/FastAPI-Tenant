import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../features/auth/context/AuthContext';
import { Loader2 } from 'lucide-react';

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { authState } = useAuth();
  const location = useLocation();

  if (authState === 'CHECKING_SESSION' || authState === 'UNKNOWN') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-slate-200">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-3" />
        <p className="text-xs text-slate-400">Verifying session...</p>
      </div>
    );
  }

  if (authState === 'SESSION_EXPIRED') {
    return <Navigate to="/session-expired" state={{ from: location }} replace />;
  }

  if (authState !== 'AUTHENTICATED') {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
