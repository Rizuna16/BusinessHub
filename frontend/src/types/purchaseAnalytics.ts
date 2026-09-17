export interface PurchaseSupplierBreakdownItem {
  supplier_id: string;
  supplier_code: string;
  supplier_name: string;
  gross_purchases: number | string;
  purchase_returns: number | string;
  net_purchases: number | string;
  purchase_count: number;
}

export interface PurchaseAnalyticsBySupplierResponse {
  date_from: string;
  date_to: string;
  gross_purchases: number | string;
  purchase_returns: number | string;
  net_purchases: number | string;
  suppliers: PurchaseSupplierBreakdownItem[];
}

export interface PurchaseCategoryBreakdownItem {
  category_id: string | null;
  category_code: string;
  category_name: string;
  gross_purchases: number | string;
  purchase_returns: number | string;
  net_purchases: number | string;
  purchase_count: number;
}

export interface PurchaseAnalyticsByCategoryResponse {
  date_from: string;
  date_to: string;
  gross_purchases: number | string;
  purchase_returns: number | string;
  net_purchases: number | string;
  categories: PurchaseCategoryBreakdownItem[];
}

export interface PurchaseAnalyticsSummaryResponse {
  date_from: string;
  date_to: string;
  gross_purchases: number | string;
  purchase_returns: number | string;
  net_purchases: number | string;
  discount_total: number | string;
  tax_total: number | string;
  purchase_count: number;
  average_purchase_value: number | string;
}