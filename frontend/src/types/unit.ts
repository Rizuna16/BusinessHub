export type UnitType = 'COUNT' | 'WEIGHT' | 'VOLUME' | 'LENGTH' | 'TIME' | 'OTHER';

export type UnitStatus = 'ACTIVE' | 'ARCHIVED';

export interface Unit {
  id: string;
  business_id: string;
  name: string;
  code: string;
  symbol?: string | null;
  description?: string | null;
  unit_type: UnitType;
  precision: number;
  status: UnitStatus;
  created_at: string;
  updated_at: string;
}

export interface UnitCreatePayload {
  name: string;
  code: string;
  symbol?: string | null;
  description?: string | null;
  unit_type?: UnitType;
  precision?: number;
}

export interface UnitUpdatePayload {
  name?: string;
  code?: string;
  symbol?: string | null;
  description?: string | null;
  unit_type?: UnitType;
  precision?: number;
}
