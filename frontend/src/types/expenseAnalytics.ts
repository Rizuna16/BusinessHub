export interface CategoryBreakdownItem {
  category_id: string | null;
  category_code: string;
  category_name: string;
  total: number | string;
  expense_count: number;
}

export interface ExpenseAnalyticsByCategoryResponse {
  date_from: string;
  date_to: string;
  total: number | string;
  expense_count: number;
  categories: CategoryBreakdownItem[];
}
