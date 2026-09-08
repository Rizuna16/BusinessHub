export type PriceListStatus = 'ACTIVE' | 'ARCHIVED';
export type PriceEntryStatus = 'ACTIVE' | 'ARCHIVED';

export interface PriceList {
  id: string;
  business_id: string;
  name: string;
  code: string;
  description: string | null;
  currency: string;
  status: PriceListStatus;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface PriceListCreate {
  name: string;
  code: string;
  description?: string | null;
  currency: string;
}

export interface PriceListListResponse {
  items: PriceList[];
  total: number;
}

export interface PriceEntry {
  id: string;
  business_id: string;
  price_list_id: string;
  product_id: string | null;
  variant_id: string | null;
  amount: string;
  currency: string;
  effective_from: string;
  effective_to: string | null;
  status: PriceEntryStatus;
  created_at: string;
  updated_at: string;
}

export interface PriceEntryCreate {
  product_id?: string;
  variant_id?: string;
  amount: string;
  effective_from: string;
  effective_to?: string | null;
}

export interface PriceEntryUpdate {
  amount?: string;
  effective_from?: string;
  effective_to?: string | null;
}

export interface PriceEntryListResponse {
  items: PriceEntry[];
  total: number;
}
