export type PayableStatus = 'UNPAID' | 'PARTIALLY_PAID' | 'PAID';

export interface PayableReturnItem {
  id: string;
  return_number: string;
  return_date: string;
  grand_total: number | string;
  status: string;
  created_at: string;
}

export interface PurchasePayableResponse {
  purchase_id: string;
  business_id: string;
  purchase_number: string;
  purchase_date: string;
  supplier_id: string;
  supplier_name?: string | null;
  supplier_code?: string | null;
  branch_id: string;
  branch_name?: string | null;
  currency: string;
  gross_payable: number | string;
  return_adjustment: number | string;
  net_payable: number | string;
  paid_amount: number | string;
  outstanding_amount: number | string;
  status: PayableStatus;
  return_count: number;
  returns: PayableReturnItem[];
}

export interface PurchasePayableListResponse {
  items: PurchasePayableResponse[];
  page: number;
  page_size: number;
  total: number;
}

export interface PurchasePayableSummaryResponse {
  currency: string;
  total_gross_payable: number | string;
  total_return_adjustment: number | string;
  total_net_payable: number | string;
  total_paid_amount: number | string;
  total_outstanding_amount: number | string;
  unpaid_count: number;
  partially_paid_count: number;
  paid_count: number;
  supplier_count: number;
}

export interface SupplierPayableSummaryItem {
  supplier_id: string;
  supplier_name?: string | null;
  supplier_code?: string | null;
  currency: string;
  total_gross_payable: number | string;
  total_return_adjustment: number | string;
  total_net_payable: number | string;
  total_paid_amount: number | string;
  total_outstanding_amount: number | string;
  purchase_count: number;
  status: PayableStatus;
}

export interface SupplierPayableSummaryListResponse {
  items: SupplierPayableSummaryItem[];
}
