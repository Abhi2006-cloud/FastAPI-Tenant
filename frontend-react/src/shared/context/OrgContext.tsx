import React, { createContext, useContext, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient, setActiveOrgId } from "../api/client.ts";
import type { OrganizationResponse, EntitlementsResponse } from "../api/types.ts";
import { useAuth } from "./AuthContext.tsx";

interface OrgContextValue {
  activeOrgId: string | null;
  activeOrg: OrganizationResponse | null;
  myOrgs: OrganizationResponse[];
  entitlements: EntitlementsResponse | null;
  role: string | null;
  isLoading: boolean;
  refetchOrgs: () => void;
  switchOrg: (orgId: string) => void;
}

const OrgContext = createContext<OrgContextValue | null>(null);

export const useOrg = () => {
  const ctx = useContext(OrgContext);
  if (!ctx) throw new Error("useOrg must be used within an OrgProvider");
  return ctx;
};

export const OrgProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const { orgId } = useParams<{ orgId?: string }>();
  const navigate = useNavigate();

  const {
    data: myOrgs = [],
    isLoading: isOrgsLoading,
    refetch: refetchOrgs,
  } = useQuery<OrganizationResponse[]>({
    queryKey: ["my-organizations", user?.id],
    queryFn: async () => {
      const res = await apiClient.get<OrganizationResponse[]>("/organizations/my");
      return res.data;
    },
    enabled: !!user,
  });

  // Keep axios layer activeOrgId in sync
  useEffect(() => {
    setActiveOrgId(orgId || null);
  }, [orgId]);

  // Find active org from list
  const activeOrg = useMemo(() => {
    if (!orgId) return myOrgs[0] || null;
    return myOrgs.find((o) => o.id === orgId) || null;
  }, [orgId, myOrgs]);

  const effectiveOrgId = activeOrg?.id || orgId || null;

  // Entitlements for active org
  const { data: entitlements = null, isLoading: isEntitlementsLoading } = useQuery<EntitlementsResponse>({
    queryKey: ["entitlements", effectiveOrgId],
    queryFn: async () => {
      if (!effectiveOrgId) throw new Error("No active org");
      const res = await apiClient.get<EntitlementsResponse>(`/organizations/${effectiveOrgId}/entitlements`);
      return res.data;
    },
    enabled: !!effectiveOrgId && !!user,
    staleTime: 30_000,
  });

  const role = activeOrg?.role || null;

  const switchOrg = (newOrgId: string) => {
    setActiveOrgId(newOrgId);
    navigate(`/o/${newOrgId}/overview`);
  };

  return (
    <OrgContext.Provider
      value={{
        activeOrgId: effectiveOrgId,
        activeOrg,
        myOrgs,
        entitlements,
        role,
        isLoading: isOrgsLoading || isEntitlementsLoading,
        refetchOrgs,
        switchOrg,
      }}
    >
      {children}
    </OrgContext.Provider>
  );
};

