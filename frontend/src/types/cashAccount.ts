export type CashAccountType = 'CASH' | 'BANK' | 'E_WALLET' | 'OTHER';
export type CashAccountStatus = 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';
export type CashMovementType = 'OPENING_BALANCE' | 'CASH_IN' | 'CASH_OUT' | 'TRANSFER_IN' | 'TRANSFER_OUT' | 'SALES_PAYMENT';
export type MovementDirection = 'IN' | 'OUT';

export interface CashAccountResponse {
  id: string;
  business_id: string;
  name: string;
  code: string;
  account_type: CashAccountType;
  currency: string;
  description?: string | null;
  opening_balance: number | string;
  status: CashAccountStatus;
  is_default: boolean;
  current_balance: number | string;
  created_at: string;
  updated_at: string;
}

export interface CashAccountListResponse {
  items: CashAccountResponse[];
  page: number;
  page_size: number;
  total: number;
}

export interface CashAccountCreateInput {
  name: string;
  code: string;
  account_type: CashAccountType;
  currency?: string;
  description?: string;
  opening_balance?: number | string;
  is_default?: boolean;
}

export interface CashAccountUpdateInput {
  name?: string;
  description?: string;
  is_default?: boolean;
}

export interface CashMovementResponse {
  id: string;
  business_id: string;
  cash_account_id: string;
  movement_type: CashMovementType;
  amount: number | string;
  direction: MovementDirection;
  reference_type?: string | null;
  reference_id?: string | null;
  description?: string | null;
  performed_by_user_id: string;
  shift_id?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CashMovementListResponse {
  items: CashMovementResponse[];
  page: number;
  page_size: number;
  total: number;
}

export interface CashMovementCreateInput {
  movement_type: CashMovementType;
  amount: number | string;
  direction: MovementDirection;
  reference_type?: string;
  reference_id?: string;
  description?: string;
}

export interface CashTransferInput {
  source_account_id: string;
  destination_account_id: string;
  amount: number | string;
  description?: string;
}

export interface CashSummaryResponse {
  total_cash_balance: number | string;
  cash_account_count: number;
  active_account_count: number;
  currency: string;
}
