export type ProductType = 'GOODS' | 'SERVICE';
export type ProductStatus = 'ACTIVE' | 'ARCHIVED';

export interface Product {
  id: string;
  business_id: string;
  category_id: string | null;
  unit_id: string;
  name: string;
  code: string;
  description: string | null;
  product_type: ProductType;
  status: ProductStatus;
  created_at: string;
  updated_at: string;
}

export interface ProductCreate {
  name: string;
  code: string;
  description?: string | null;
  category_id?: string | null;
  unit_id: string;
  product_type: ProductType;
}

export interface ProductUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  category_id?: string | null;
  unit_id?: string;
  product_type?: ProductType;
}

export interface ProductListResponse {
  items: Product[];
  page: number;
  page_size: number;
  total: number;
}

// Product Variant
export type ProductVariantStatus = 'ACTIVE' | 'ARCHIVED';

export interface ProductVariant {
  id: string;
  business_id: string;
  product_id: string;
  name: string;
  code: string;
  attributes?: Record<string, unknown> | null;
  status: ProductVariantStatus;
  created_at: string;
  updated_at: string;
}

export interface ProductVariantCreate {
  name: string;
  code: string;
  attributes?: Record<string, unknown> | null;
}

export interface ProductVariantUpdate {
  name?: string;
  code?: string;
  attributes?: Record<string, unknown> | null;
}

export interface ProductVariantListResponse {
  items: ProductVariant[];
  total: number;
}

export interface ProductImage {
  id: string;
  business_id: string;
  product_id: string;
  variant_id: string | null;
  storage_key: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  sort_order: number;
  is_primary: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

// Barcode
export type BarcodeType = 'EAN13' | 'EAN8' | 'UPC_A' | 'CODE128' | 'OTHER';
export type BarcodeStatus = 'ACTIVE' | 'ARCHIVED';

export interface Barcode {
  id: string;
  business_id: string;
  product_id: string | null;
  variant_id: string | null;
  code: string;
  barcode_type: BarcodeType;
  status: BarcodeStatus;
  created_at: string;
  updated_at: string;
}

export interface BarcodeCreate {
  code: string;
  barcode_type?: BarcodeType;
  product_id?: string | null;
  variant_id?: string | null;
}

export interface BarcodeUpdate {
  code?: string;
  barcode_type?: BarcodeType;
}

export interface BarcodeListResponse {
  items: Barcode[];
  total: number;
}
