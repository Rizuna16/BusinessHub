export interface Account {
  id: string;
  user_id: string;
  display_name: string | null;
  phone: string | null;
  avatar_url: string | null;
  timezone: string;
  locale: string;
  created_at: string;
  updated_at: string;
}

export interface AccountUpdatePayload {
  display_name?: string;
  phone?: string | null;
  avatar_url?: string | null;
  timezone?: string;
  locale?: string;
}
