export interface ProductProfitabilityPeriodInfo {
  date_from: string;
  date_to: string;
  period_name: string | null;
}

export interface ProductProfitabilityItem {
  group_id: string;
  group_name: string;
  group_code: string | null;
  category_name: string | null;
  customer_name: string | null;
  branch_name: string | null;
  net_revenue: string;
  total_discount: string;
  total_tax: string;
  gross_sales: string;
  cogs: string;
  gross_profit: string;
  gross_margin_percentage: string | null;
  units_sold: string;
  units_returned: string;
  sales_count: number;
  return_count: number;
}

export interface ProductProfitabilitySummary {
  total_net_revenue: string;
  total_cogs: string;
  total_gross_profit: string;
  overall_gross_margin_percentage: string | null;
  total_sales_count: number;
  total_return_count: number;
  total_units_sold: string;
  total_units_returned: string;
}

export interface ProductProfitabilityResponse {
  business_id: string;
  period: ProductProfitabilityPeriodInfo;
  summary: ProductProfitabilitySummary;
  items: ProductProfitabilityItem[];
}