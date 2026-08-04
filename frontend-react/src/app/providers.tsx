import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../features/auth/context/AuthContext';
import { OrgProvider } from '../features/organizations/context/OrgContext';
import { ToastProvider } from '../shared/components/ui/Toast';
import '../shared/i18n';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 60 * 5, // 5 minutes cache
    },
  },
});

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <OrgProvider>
          <ToastProvider>{children}</ToastProvider>
        </OrgProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
