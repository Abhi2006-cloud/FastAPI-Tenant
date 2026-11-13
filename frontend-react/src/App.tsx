import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./shared/context/AuthContext.tsx";
import { OrgProvider } from "./shared/context/OrgContext.tsx";
import { ToastProvider } from "./shared/components/Toast.tsx";
import { ErrorBoundary } from "./shared/components/ErrorBoundary.tsx";
import { AppLayout } from "./layout/AppLayout.tsx";

// Pages
import { LoginPage } from "./pages/auth/LoginPage.tsx";
import { RegisterPage } from "./pages/auth/RegisterPage.tsx";
import { CreateOrgPage } from "./pages/organizations/CreateOrgPage.tsx";
import { OverviewPage } from "./pages/dashboard/OverviewPage.tsx";
import { MembersPage } from "./pages/members/MembersPage.tsx";
import { InvitationsPage } from "./pages/invitations/InvitationsPage.tsx";
import { FilesPage } from "./pages/files/FilesPage.tsx";
import { SearchPage } from "./pages/search/SearchPage.tsx";
import { AuditPage } from "./pages/audit/AuditPage.tsx";
import { BillingPage } from "./pages/billing/BillingPage.tsx";
import { SettingsPage } from "./pages/settings/SettingsPage.tsx";
import { SecurityPage } from "./pages/account/SecurityPage.tsx";
import { PlatformPage } from "./pages/platform/PlatformPage.tsx";
import { SearchDocPage } from "./pages/docs/SearchDocPage.tsx";
import { EmailDocPage } from "./pages/docs/EmailDocPage.tsx";
import { AcceptInvitePage } from "./pages/invitations/AcceptInvitePage.tsx";
import { NotFoundPage } from "./pages/NotFoundPage.tsx";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Guard component that checks if user is authenticated
const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center">
        <div className="h-6 w-24 bg-[#E4E4E7]/60 rounded animate-pulse" />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

// Root index redirector
const RootRedirect: React.FC = () => {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to="/platform" replace />;
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <ToastProvider>
              <Routes>
                {/* Public Routes */}
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/docs/search" element={<SearchDocPage />} />
                <Route path="/docs/email" element={<EmailDocPage />} />
                <Route path="/platform" element={<PlatformPage />} />
                <Route
                  path="/invitations"
                  element={
                    <OrgProvider>
                      <AcceptInvitePage />
                    </OrgProvider>
                  }
                />
                <Route
                  path="/accept-invite"
                  element={
                    <OrgProvider>
                      <AcceptInvitePage />
                    </OrgProvider>
                  }
                />

                {/* Root Redirect */}
                <Route path="/" element={<RootRedirect />} />

                {/* Create Org */}
                <Route
                  path="/o/new"
                  element={
                    <RequireAuth>
                      <OrgProvider>
                        <CreateOrgPage />
                      </OrgProvider>
                    </RequireAuth>
                  }
                />

                {/* Tenant Workspace Routes */}
                <Route
                  path="/o/:orgId"
                  element={
                    <RequireAuth>
                      <OrgProvider>
                        <AppLayout />
                      </OrgProvider>
                    </RequireAuth>
                  }
                >
                  <Route index element={<Navigate to="overview" replace />} />
                  <Route path="overview" element={<OverviewPage />} />
                  <Route path="members" element={<MembersPage />} />
                  <Route path="invitations" element={<InvitationsPage />} />
                  <Route path="files" element={<FilesPage />} />
                  <Route path="search" element={<SearchPage />} />
                  <Route path="audit" element={<AuditPage />} />
                  <Route path="billing" element={<BillingPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                </Route>

                {/* User Account Security Route */}
                <Route
                  path="/account/security"
                  element={
                    <RequireAuth>
                      <OrgProvider>
                        <AppLayout />
                      </OrgProvider>
                    </RequireAuth>
                  }
                >
                  <Route index element={<SecurityPage />} />
                </Route>

                {/* 404 Fallback */}
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </ToastProvider>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};

