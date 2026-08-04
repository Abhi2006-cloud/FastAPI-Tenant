export interface User {
  id: string;
  email: string;
  created_at: string;
  updated_at?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface UserRegister {
  email: string;
  password: string;
}

export interface SessionItem {
  id: string;
  device_name?: string | null;
  platform?: string | null;
  browser?: string | null;
  ip_address?: string | null;
  created_at: string;
  last_used_at: string;
  expires_at: string;
  is_current: boolean;
  is_active: boolean;
}
