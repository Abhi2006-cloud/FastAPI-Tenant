import React from 'react';
import { useOrg } from '../../features/organizations/context/OrgContext';
import { AlertCircle } from 'lucide-react';
import { Alert } from '../components/ui/Alert';

export function RequireRole({
  allowedRoles,
  children,
}: {
  allowedRoles: string[];
  children: React.ReactNode;
}) {
  const { userRoleInActiveOrg } = useOrg();

  if (userRoleInActiveOrg && !allowedRoles.includes(userRoleInActiveOrg)) {
    return (
      <div className="p-6">
        <Alert variant="danger" title="Access Restricted">
          You do not have permission to view or manage this feature. (Required role:{' '}
          {allowedRoles.join(', ')}). Your current role is <strong>{userRoleInActiveOrg}</strong>.
        </Alert>
      </div>
    );
  }

  return <>{children}</>;
}
