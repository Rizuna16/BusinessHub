export type AgingBucket = 'CURRENT' | '1_30' | '31_60' | '61_90' | '91_120' | 'OVER_120';

export interface ARInvoiceAgingItem {
  sales_id: string;
  sales_number: string;
  sales_date: string;
  customer_id?: string | null;
  customer_name?: string | null;
  branch_id: string;
  branch_name?: string | null;
  original_amount: number | string;
  return_adjustment: number | string;
  paid_amount: number | string;
  outstanding_amount: number | string;
  aging_days: number;
  aging_bucket: AgingBucket;
}

export interface ARCustomerAgingSummaryItem {
  customer_id?: string | null;
  customer_name?: string | null;
  total_original: number | string;
  total_return_adjustment: number | string;
  total_paid: number | string;
  total_outstanding: number | string;
  invoice_count: number;
  current: number | string;
  bucket_1_30: number | string;
  bucket_31_60: number | string;
  bucket_61_90: number | string;
  bucket_91_120: number | string;
  bucket_over_120: number | string;
}

export interface ARAgingSummary {
  total_original: number | string;
  total_return_adjustment: number | string;
  total_paid: number | string;
  total_outstanding: number | string;
  current: number | string;
  bucket_1_30: number | string;
  bucket_31_60: number | string;
  bucket_61_90: number | string;
  bucket_91_120: number | string;
  bucket_over_120: number | string;
}

export interface ARAgingResponse {
  as_of_date: string;
  summary: ARAgingSummary;
  customers: ARCustomerAgingSummaryItem[];
  invoices: ARInvoiceAgingItem[];
}

export interface APInvoiceAgingItem {
  purchase_id: string;
  purchase_number: string;
  purchase_date: string;
  supplier_id: string;
  supplier_name?: string | null;
  supplier_code?: string | null;
  branch_id: string;
  branch_name?: string | null;
  gross_payable: number | string;
  return_adjustment: number | string;
  paid_amount: number | string;
  outstanding_amount: number | string;
  aging_days: number;
  aging_bucket: AgingBucket;
}

export interface APSupplierAgingSummaryItem {
  supplier_id: string;
  supplier_name?: string | null;
  supplier_code?: string | null;
  total_gross: number | string;
  total_return_adjustment: number | string;
  total_paid: number | string;
  total_outstanding: number | string;
  purchase_count: number;
  current: number | string;
  bucket_1_30: number | string;
  bucket_31_60: number | string;
  bucket_61_90: number | string;
  bucket_91_120: number | string;
  bucket_over_120: number | string;
}

export interface APAgingSummary {
  total_gross: number | string;
  total_return_adjustment: number | string;
  total_paid: number | string;
  total_outstanding: number | string;
  current: number | string;
  bucket_1_30: number | string;
  bucket_31_60: number | string;
  bucket_61_90: number | string;
  bucket_91_120: number | string;
  bucket_over_120: number | string;
}

export interface APAgingResponse {
  as_of_date: string;
  summary: APAgingSummary;
  suppliers: APSupplierAgingSummaryItem[];
  purchases: APInvoiceAgingItem[];
}
