export type PaymentDirection = 'CUSTOMER_IN' | 'SUPPLIER_OUT';
export type PaymentTargetType = 'SALES' | 'PURCHASE';
export type PaymentMethod = 'CASH' | 'BANK_TRANSFER' | 'DEBIT_CARD' | 'CREDIT_CARD' | 'QRIS' | 'E_WALLET' | 'OTHER';
export type PaymentStatus = 'RECORDED' | 'VOIDED';

export interface Payment {
  id: string;
  business_id: string;
  branch_id: string;
  direction: PaymentDirection;
  target_type: PaymentTargetType;
  target_id: string;
  payment_number: string;
  payment_date: string;
  payment_method: PaymentMethod;
  amount: number | string;
  currency: string;
  cash_account_id: string;
  reference_number?: string | null;
  notes?: string | null;
  status: PaymentStatus;
  created_by_user_id: string;
  voided_by_user_id?: string | null;
  idempotency_key?: string | null;
  created_at: string;
  updated_at: string;
  voided_at?: string | null;
}

export interface PaymentListResponse {
  items: Payment[];
  page: number;
  page_size: number;
  total: number;
}
