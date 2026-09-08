export type WarehouseStatus = 'ACTIVE' | 'SUSPENDED' | 'ARCHIVED';

export type InventoryLocationType =
  | 'GENERAL'
  | 'RECEIVING'
  | 'STORAGE'
  | 'PICKING'
  | 'SHIPPING'
  | 'DAMAGED'
  | 'QUARANTINE'
  | 'OTHER';

export type InventoryLocationStatus = 'ACTIVE' | 'ARCHIVED';

export interface Warehouse {
  id: string;
  business_id: string;
  branch_id: string | null;
  name: string;
  code: string;
  description: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  status: WarehouseStatus;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface WarehouseCreatePayload {
  name: string;
  code: string;
  description?: string;
  address?: string;
  phone?: string;
  email?: string;
  branch_id?: string | null;
}

export interface WarehouseUpdatePayload {
  name?: string;
  description?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  branch_id?: string | null;
}

export interface InventoryLocation {
  id: string;
  business_id: string;
  warehouse_id: string;
  name: string;
  code: string;
  description: string | null;
  location_type: InventoryLocationType;
  status: InventoryLocationStatus;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryLocationCreatePayload {
  name: string;
  code: string;
  description?: string;
  location_type?: InventoryLocationType;
}

export interface InventoryLocationUpdatePayload {
  name?: string;
  description?: string | null;
  location_type?: InventoryLocationType;
}
