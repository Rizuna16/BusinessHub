export type PurchaseStatus = 'DRAFT' | 'FINALIZED' | 'CANCELLED';
export type DerivedReceivingStatus = 'NOT_RECEIVED' | 'PARTIALLY_RECEIVED' | 'FULLY_RECEIVED';

export interface PurchaseReceivingSummary {
    total_ordered: string;
    total_received: string;
    total_remaining: string;
    status: DerivedReceivingStatus;
}

export interface PurchaseLineResponse {
    id: string;
    purchase_id: string;
    product_id: string;
    variant_id?: string | null;
    description?: string | null;
    quantity: number | string;
    unit_price: number | string;
    discount_amount: number | string;
    tax_amount: number | string;
    line_subtotal: number | string;
    line_total: number | string;
    created_at: string;
    updated_at: string;

    ordered_quantity?: string;
    received_quantity?: string;
    remaining_quantity?: string;
    suggested_supplier_price?: string | null;
}

export interface PurchaseResponse {
    id: string;
    business_id: string;
    supplier_id: string;
    branch_id: string;
    purchase_number: string;
    purchase_date: string;
    notes?: string | null;
    status: PurchaseStatus;
    subtotal: number | string;
    discount_total: number | string;
    tax_total: number | string;
    grand_total: number | string;
    created_by_user_id: string;
    finalized_by_user_id?: string | null;
    cancelled_by_user_id?: string | null;
    is_deleted: boolean;
    created_at: string;
    updated_at: string;
    finalized_at?: string | null;
    cancelled_at?: string | null;
    lines: PurchaseLineResponse[];
    receiving_summary?: PurchaseReceivingSummary | null;
}

export interface PurchaseListResponse {
    items: PurchaseResponse[];
    page: number;
    page_size: number;
    total: number;
}

export interface PurchaseCreateInput {
    supplier_id: string;
    branch_id: string;
    purchase_date: string;
    notes?: string;
}

export interface PurchaseUpdateInput {
    supplier_id?: string;
    branch_id?: string;
    purchase_date?: string;
    notes?: string;
}

export interface PurchaseLineCreateInput {
    product_id: string;
    variant_id?: string | null;
    description?: string;
    quantity: number;
    unit_price: number;
    discount_amount?: number;
    tax_amount?: number;
}

export interface PurchaseLineUpdateInput {
    product_id?: string;
    variant_id?: string | null;
    description?: string;
    quantity?: number;
    unit_price?: number;
    discount_amount?: number;
    tax_amount?: number;
}
