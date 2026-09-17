export type PlatformRole = 'SUPER_ADMIN' | null;

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  platform_role: PlatformRole;
  created_at: string;
  updated_at: string;
}

export interface RegisterPayload {
  email: string;
  full_name: string;
  password: string;
  password_confirmation: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiResponse<T = any> {
  success?: boolean;
  message?: string;
  errors?: string[];
  data?: T;
}
