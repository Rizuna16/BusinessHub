export interface SalesAnalyticsSummaryResponse {
  date_from: string;
  date_to: string;
  gross_sales: number | string;
  sales_returns: number | string;
  net_sales: number | string;
  discount_total: number | string;
  tax_total: number | string;
  transaction_count: number;
  average_transaction_value: number | string;
}

export interface SalesCategoryBreakdownItem {
  category_id: string | null;
  category_code: string;
  category_name: string;
  gross_sales: number | string;
  sales_returns: number | string;
  net_sales: number | string;
  transaction_count: number;
}

export interface SalesAnalyticsByCategoryResponse {
  date_from: string;
  date_to: string;
  gross_sales: number | string;
  sales_returns: number | string;
  net_sales: number | string;
  categories: SalesCategoryBreakdownItem[];
}

export interface SalesCustomerBreakdownItem {
  customer_id: string | null;
  customer_code: string;
  customer_name: string;
  gross_sales: number | string;
  sales_returns: number | string;
  net_sales: number | string;
  transaction_count: number;
}

export interface SalesAnalyticsByCustomerResponse {
  date_from: string;
  date_to: string;
  gross_sales: number | string;
  sales_returns: number | string;
  net_sales: number | string;
  customers: SalesCustomerBreakdownItem[];
}
