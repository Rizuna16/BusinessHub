export type AccountType = 'ASSET' | 'LIABILITY' | 'EQUITY' | 'REVENUE' | 'EXPENSE';
export type AccountingPeriodStatus = 'OPEN' | 'CLOSED';

export interface AccountingPeriod {
  id: string;
  business_id: string;
  period_name: string;
  start_date: string;
  end_date: string;
  status: AccountingPeriodStatus;
  created_at: string;
  created_by_user_id: string;
  updated_at: string;
  closed_at?: string | null;
  closed_by_user_id?: string | null;
}

export interface AccountingPeriodListResponse {
  items: AccountingPeriod[];
  total: number;
}

export interface AccountingPeriodCreatePayload {
  period_name: string;
  start_date: string;
  end_date: string;
}
export type NormalBalance = 'DEBIT' | 'CREDIT';
export type JournalStatus = 'DRAFT' | 'POSTED' | 'VOIDED';

export interface Account {
  id: string;
  business_id: string;
  code: string;
  name: string;
  account_type: AccountType;
  normal_balance: NormalBalance;
  parent_id?: string | null;
  is_active: boolean;
  is_system: boolean;
  description?: string | null;
  created_at: string;
  updated_at: string;
  current_balance: number | string;
}

export interface AccountListResponse {
  items: Account[];
  total: number;
}

export interface JournalLine {
  id: string;
  journal_entry_id: string;
  account_id: string;
  account_code?: string | null;
  account_name?: string | null;
  description?: string | null;
  debit: number | string;
  credit: number | string;
  currency: string;
}

export interface JournalEntry {
  id: string;
  business_id: string;
  branch_id?: string | null;
  journal_number: string;
  journal_date: string;
  description: string;
  reference_type?: string | null;
  reference_id?: string | null;
  status: JournalStatus;
  source: string;
  total_debit: number | string;
  total_credit: number | string;
  currency: string;
  posted_at?: string | null;
  posted_by_user_id?: string | null;
  voided_at?: string | null;
  voided_by_user_id?: string | null;
  idempotency_key?: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
  lines: JournalLine[];
}

export interface JournalEntryListResponse {
  items: JournalEntry[];
  page: number;
  page_size: number;
  total: number;
}

export interface GeneralLedgerResponse {
  account_id: string;
  account_code: string;
  account_name: string;
  account_type: AccountType;
  normal_balance: NormalBalance;
  opening_balance: number | string;
  total_debit: number | string;
  total_credit: number | string;
  ending_balance: number | string;
  lines: {
    journal_id: string;
    journal_number: string;
    journal_date: string;
    description: string;
    reference_type?: string | null;
    reference_id?: string | null;
    debit: number | string;
    credit: number | string;
    running_balance: number | string;
  }[];
}

export interface TrialBalanceResponse {
  currency: string;
  total_debit: number | string;
  total_credit: number | string;
  is_balanced: boolean;
  items: {
    account_id: string;
    account_code: string;
    account_name: string;
    account_type: AccountType;
    normal_balance: NormalBalance;
    debit_balance: number | string;
    credit_balance: number | string;
  }[];
}

export interface ReportAccountItem {
  account_id: string;
  account_code: string;
  account_name: string;
  amount: number | string;
}

export interface ProfitAndLossResponse {
  period: AccountingPeriod;
  revenue_items: ReportAccountItem[];
  total_revenue: number | string;
  expense_items: ReportAccountItem[];
  total_expense: number | string;
  net_profit: number | string;
}

export interface BalanceSheetItem {
  account_id: string;
  account_code: string;
  account_name: string;
  balance: number | string;
}

export interface BalanceSheetResponse {
  period: AccountingPeriod;
  as_of_date: string;
  asset_items: BalanceSheetItem[];
  total_assets: number | string;
  liability_items: BalanceSheetItem[];
  total_liabilities: number | string;
  equity_items: BalanceSheetItem[];
  total_equity: number | string;
  net_profit_current_period: number | string;
  total_liabilities_and_equity: number | string;
  is_balanced: boolean;
}

export interface TaxSummaryResponse {
  year: number;
  month: number;
  output_vat: number | string;
  input_vat: number | string;
  net_vat: number | string;
  taxable_sales_count: number;
  taxable_purchase_count: number;
}
