export interface Organization {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
  updated_at?: string;
}

export interface OrganizationCreate {
  name: string;
}

export interface OrganizationUpdate {
  name: string;
}
