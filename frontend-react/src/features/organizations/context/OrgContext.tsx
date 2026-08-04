import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { storage } from '../../../shared/utils/storage';
import { apiClient } from '../../../shared/api/client';
import { Organization } from '../types';
import { useAuth } from '../../auth/context/AuthContext';

interface OrgContextType {
  organizations: Organization[];
  activeOrg: Organization | null;
  isLoading: boolean;
  userRoleInActiveOrg: string | null;
  selectOrg: (orgId: string) => void;
  fetchOrganizations: () => Promise<void>;
}

const OrgContext = createContext<OrgContextType | undefined>(undefined);

export function OrgProvider({ children }: { children: React.ReactNode }) {
  const { authState } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [activeOrg, setActiveOrg] = useState<Organization | null>(null);
  const [userRoleInActiveOrg, setUserRoleInActiveOrg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchOrganizations = useCallback(async () => {
    if (authState !== 'AUTHENTICATED') return;
    setIsLoading(true);
    try {
      const response = await apiClient.get<Organization[]>('/organizations/my');
      const orgs = response.data;
      setOrganizations(orgs);

      const storedOrgId = storage.getActiveOrgId();
      if (storedOrgId && orgs.some((o) => o.id === storedOrgId)) {
        const found = orgs.find((o) => o.id === storedOrgId)!;
        setActiveOrg(found);
      } else if (orgs.length > 0) {
        setActiveOrg(orgs[0]);
        storage.setActiveOrgId(orgs[0].id);
      } else {
        setActiveOrg(null);
      }
    } catch {
      setOrganizations([]);
      setActiveOrg(null);
    } finally {
      setIsLoading(false);
    }
  }, [authState]);

  const fetchUserRole = useCallback(async (orgId: string) => {
    try {
      const response = await apiClient.get(`/organizations/${orgId}/members`);
      const members = response.data;
      const meResponse = await apiClient.get('/auth/me');
      const currentUserId = meResponse.data.id;
      const myMembership = members.find((m: { user_id: string; role: string }) => m.user_id === currentUserId);
      if (myMembership) {
        setUserRoleInActiveOrg(myMembership.role);
      }
    } catch {
      setUserRoleInActiveOrg(null);
    }
  }, []);

  useEffect(() => {
    if (authState === 'AUTHENTICATED') {
      fetchOrganizations();
    } else {
      setOrganizations([]);
      setActiveOrg(null);
      setUserRoleInActiveOrg(null);
    }
  }, [authState, fetchOrganizations]);

  useEffect(() => {
    if (activeOrg) {
      fetchUserRole(activeOrg.id);
    } else {
      setUserRoleInActiveOrg(null);
    }
  }, [activeOrg, fetchUserRole]);

  const selectOrg = (orgId: string) => {
    const found = organizations.find((o) => o.id === orgId);
    if (found) {
      setActiveOrg(found);
      storage.setActiveOrgId(orgId);
    }
  };

  return (
    <OrgContext.Provider
      value={{
        organizations,
        activeOrg,
        isLoading,
        userRoleInActiveOrg,
        selectOrg,
        fetchOrganizations,
      }}
    >
      {children}
    </OrgContext.Provider>
  );
}

export function useOrg() {
  const context = useContext(OrgContext);
  if (!context) {
    throw new Error('useOrg must be used within an OrgProvider');
  }
  return context;
}
