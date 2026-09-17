export interface DashboardPeriodInfo {
  date_from: string;
  date_to: string;
}

export interface DashboardRevenue {
  total: string;
  sales_count: number;
  return_count: number;
  net: string;
}

export interface DashboardExpenses {
  total: string;
  expense_count: number;
}

export interface DashboardCashPosition {
  total_balance: string;
  account_count: number;
}

export interface DashboardReceivables {
  total_outstanding: string;
  unpaid_count: number;
  partially_paid_count: number;
}

export interface DashboardPayables {
  total_outstanding: string;
  unpaid_count: number;
  partially_paid_count: number;
}

export interface DashboardInventory {
  total_items: number;
  total_valuation: string;
}

export interface DashboardActivityItem {
  date: string;
  type: string;
  reference: string;
  amount: string;
  status: string;
}

export interface OperationalDashboardResponse {
  period: DashboardPeriodInfo;
  revenue: DashboardRevenue;
  expenses: DashboardExpenses;
  net_operating_result: string;
  cash_position: DashboardCashPosition;
  receivables: DashboardReceivables;
  payables: DashboardPayables;
  inventory: DashboardInventory;
  recent_activity: DashboardActivityItem[];
}