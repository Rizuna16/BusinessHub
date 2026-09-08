export type BusinessMembershipRole = 'OWNER' | 'ADMIN' | 'MEMBER';

export type BusinessMembershipStatus = 'ACTIVE' | 'SUSPENDED' | 'REMOVED';

export interface BusinessMembership {
  id: string;
  business_id: string;
  user_id: string;
  role: BusinessMembershipRole;
  status: BusinessMembershipStatus;
  created_at: string;
  updated_at: string;
  email?: string | null;
  display_name?: string | null;
}

export interface AddBusinessMemberInput {
  user_id: string;
  role: BusinessMembershipRole;
}

export interface UpdateBusinessMemberInput {
  role?: BusinessMembershipRole;
  status?: BusinessMembershipStatus;
}
