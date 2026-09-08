export type SupplierCatalogStatus = 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';

export interface SupplierCatalogItem {
  id: string;
  business_id: string;
  supplier_id: string;
  product_id?: string | null;
  variant_id?: string | null;
  supplier_code?: string | null;
  supplier_product_name?: string | null;
  purchase_price: string;
  currency: string;
  minimum_order_quantity?: string | null;
  lead_time_days?: number | null;
  is_preferred: boolean;
  status: SupplierCatalogStatus;
  notes?: string | null;
  created_at: string;
  updated_at: string;

  supplier_name?: string | null;
  product_name?: string | null;
  product_code?: string | null;
  variant_name?: string | null;
  variant_code?: string | null;
}

export interface SupplierCatalogItemCreatePayload {
  supplier_id: string;
  product_id?: string | null;
  variant_id?: string | null;
  supplier_code?: string | null;
  supplier_product_name?: string | null;
  purchase_price: number | string;
  currency?: string;
  minimum_order_quantity?: number | string | null;
  lead_time_days?: number | null;
  is_preferred?: boolean;
  notes?: string | null;
}

export interface SupplierCatalogItemUpdatePayload {
  supplier_code?: string | null;
  supplier_product_name?: string | null;
  purchase_price?: number | string;
  currency?: string;
  minimum_order_quantity?: number | string | null;
  lead_time_days?: number | null;
  is_preferred?: boolean;
  notes?: string | null;
}

export interface SupplierCatalogItemListResponse {
  items: SupplierCatalogItem[];
  page: number;
  page_size: number;
  total: number;
}
