import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '../shared/layouts/MainLayout';
import { RequireAuth } from '../shared/guards/RequireAuth';
import { RequireOrg } from '../shared/guards/RequireOrg';
import { ErrorBoundaryFallback } from '../shared/components/feedback/ErrorBoundaryFallback';

// Pages
import { LoginPage } from '../features/auth/pages/LoginPage';
import { RegisterPage } from '../features/auth/pages/RegisterPage';
import { SessionExpiredPage } from '../features/auth/pages/SessionExpiredPage';
import { AcceptInvitePage } from '../features/invitations/pages/AcceptInvitePage';

import { DashboardPage } from '../features/dashboard/pages/DashboardPage';
import { OrganizationsPage } from '../features/organizations/pages/OrganizationsPage';
import { MembersPage } from '../features/memberships/pages/MembersPage';
import { FilesPage } from '../features/files/pages/FilesPage';
import { SearchPage } from '../features/search/pages/SearchPage';
import { SessionsPage } from '../features/sessions/pages/SessionsPage';
import { EmailPage } from '../features/email/pages/EmailPage';
import { AuditLogsPage } from '../features/audit/pages/AuditLogsPage';
import { JobsPage } from '../features/jobs/pages/JobsPage';
import { ProfilePage } from '../features/profile/pages/ProfilePage';
import { NotFoundPage } from '../features/errors/pages/NotFoundPage';

export const router = createBrowserRouter([
  // Public Auth Routes
  {
    path: '/login',
    element: <LoginPage />,
    errorElement: <ErrorBoundaryFallback />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
    errorElement: <ErrorBoundaryFallback />,
  },
  {
    path: '/session-expired',
    element: <SessionExpiredPage />,
    errorElement: <ErrorBoundaryFallback />,
  },
  {
    path: '/invitations',
    element: <AcceptInvitePage />,
    errorElement: <ErrorBoundaryFallback />,
  },

  // Protected Routes wrapped in MainLayout
  {
    path: '/',
    element: (
      <RequireAuth>
        <MainLayout />
      </RequireAuth>
    ),
    errorElement: <ErrorBoundaryFallback />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'organizations',
        element: <OrganizationsPage />,
      },
      {
        path: 'members',
        element: (
          <RequireOrg>
            <MembersPage />
          </RequireOrg>
        ),
      },
      {
        path: 'files',
        element: (
          <RequireOrg>
            <FilesPage />
          </RequireOrg>
        ),
      },
      {
        path: 'search',
        element: <SearchPage />,
      },
      {
        path: 'sessions',
        element: <SessionsPage />,
      },
      {
        path: 'email',
        element: <EmailPage />,
      },
      {
        path: 'audit',
        element: <AuditLogsPage />,
      },
      {
        path: 'jobs',
        element: <JobsPage />,
      },
      {
        path: 'profile',
        element: <ProfilePage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
