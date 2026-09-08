export type ExpenseStatus = 'DRAFT' | 'FINALIZED' | 'CANCELLED';
export type ExpenseCategoryStatus = 'ACTIVE' | 'ARCHIVED';

export interface ExpenseCategoryResponse {
  id: string;
  business_id: string;
  name: string;
  code: string;
  description?: string | null;
  status: ExpenseCategoryStatus;
  created_at: string;
  updated_at: string;
}

export interface ExpenseCategoryListResponse {
  items: ExpenseCategoryResponse[];
  page: number;
  page_size: number;
  total: number;
}

export interface ExpenseCategoryCreateInput {
  name: string;
  code: string;
  description?: string;
}

export interface ExpenseCategoryUpdateInput {
  name?: string;
  description?: string;
}

export interface ExpenseResponse {
  id: string;
  business_id: string;
  expense_number: string;
  expense_date: string;
  category_id: string;
  cash_account_id?: string | null;
  supplier_id?: string | null;
  amount: number | string;
  currency: string;
  description?: string | null;
  status: ExpenseStatus;
  created_by_user_id: string;
  finalized_by_user_id?: string | null;
  cancelled_by_user_id?: string | null;
  created_at: string;
  updated_at: string;
  finalized_at?: string | null;
  cancelled_at?: string | null;
  category_name?: string | null;
  cash_account_name?: string | null;
  supplier_name?: string | null;
}

export interface ExpenseListResponse {
  items: ExpenseResponse[];
  page: number;
  page_size: number;
  total: number;
}

export interface ExpenseCreateInput {
  category_id: string;
  cash_account_id?: string;
  supplier_id?: string;
  expense_date: string;
  amount: number | string;
  currency?: string;
  description?: string;
}

export interface ExpenseUpdateInput {
  category_id?: string;
  cash_account_id?: string;
  supplier_id?: string;
  expense_date?: string;
  amount?: number | string;
  currency?: string;
  description?: string;
}

export interface ExpenseSummaryResponse {
  total_expense_amount: number | string;
  expense_count: number;
  finalized_count: number;
  draft_count: number;
  currency: string;
}
