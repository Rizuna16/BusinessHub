export type ReceivableStatus = 'UNPAID' | 'PARTIALLY_PAID' | 'PAID';

export interface ReceivablePaymentItem {
  id: string;
  payment_number: string;
  payment_date: string;
  payment_method: string;
  amount: number | string;
  reference_number?: string | null;
  notes?: string | null;
  status: string;
  created_by_user_id: string;
  created_at: string;
}

export interface SalesReceivableResponse {
  sales_id: string;
  business_id: string;
  sales_number: string;
  sales_date: string;
  customer_id?: string | null;
  customer_name?: string | null;
  branch_id: string;
  branch_name?: string | null;
  sales_total: number | string;
  paid_amount: number | string;
  outstanding_amount: number | string;
  status: ReceivableStatus;
  payment_count: number;
  last_payment_date?: string | null;
  payments: ReceivablePaymentItem[];
}

export interface SalesReceivableListResponse {
  items: SalesReceivableResponse[];
  page: number;
  page_size: number;
  total: number;
}

export interface SalesReceivableSummaryResponse {
  total_sales_amount: number | string;
  total_paid_amount: number | string;
  total_outstanding_amount: number | string;
  unpaid_count: number;
  partially_paid_count: number;
  paid_count: number;
}

export interface CustomerReceivableSummaryItem {
  customer_id?: string | null;
  customer_name?: string | null;
  total_sales: number | string;
  total_paid: number | string;
  total_outstanding: number | string;
  sales_count: number;
}

export interface CustomerReceivableSummaryListResponse {
  items: CustomerReceivableSummaryItem[];
}
