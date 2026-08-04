import React from 'react';
import { useOrg } from '../../features/organizations/context/OrgContext';
import { Building2, Plus } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { useNavigate } from 'react-router-dom';

export function RequireOrg({ children }: { children: React.ReactNode }) {
  const { activeOrg, isLoading } = useOrg();
  const navigate = useNavigate();

  if (isLoading) {
    return <div className="p-8 text-center text-slate-400 text-sm">Loading organization context...</div>;
  }

  if (!activeOrg) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-full mb-4">
          <Building2 className="w-10 h-10 text-blue-400" />
        </div>
        <h3 className="text-xl font-bold text-slate-100">No Organization Selected</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-sm">
          Please select or create an organization to access team workspace features.
        </p>
        <div className="mt-6 flex gap-3">
          <Button onClick={() => navigate('/organizations')} leftIcon={<Plus className="w-4 h-4" />}>
            Create or Select Organization
          </Button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
