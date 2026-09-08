export type SalesStatus = 'DRAFT' | 'FINALIZED' | 'CANCELLED';

export interface SalesLineResponse {
    id: string;
    sales_id: string;
    product_id?: string | null;
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
    suggested_selling_price?: string | null;
}

export interface SalesResponse {
    id: string;
    business_id: string;
    customer_id?: string | null;
    branch_id: string;
    sales_number: string;
    sales_date: string;
    notes?: string | null;
    status: SalesStatus;
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
    lines: SalesLineResponse[];
}

export interface SalesListResponse {
    items: SalesResponse[];
    page: number;
    page_size: number;
    total: number;
}

export interface SalesCreateInput {
    customer_id?: string | null;
    branch_id: string;
    sales_date: string;
    notes?: string | null;
}

export interface SalesUpdateInput {
    customer_id?: string | null;
    branch_id?: string;
    sales_date?: string;
    notes?: string | null;
}

export interface SalesLineCreateInput {
    product_id?: string | null;
    variant_id?: string | null;
    description?: string;
    quantity: number | string;
    unit_price: number | string;
    discount_amount?: number | string;
    tax_amount?: number | string;
}

export interface SalesLineUpdateInput {
    product_id?: string | null;
    variant_id?: string | null;
    description?: string;
    quantity?: number | string;
    unit_price?: number | string;
    discount_amount?: number | string;
    tax_amount?: number | string;
}

export type PaymentMethod =
    | 'CASH'
    | 'BANK_TRANSFER'
    | 'DEBIT_CARD'
    | 'CREDIT_CARD'
    | 'QRIS'
    | 'E_WALLET'
    | 'OTHER';

export type PaymentStatus = 'RECORDED' | 'CANCELLED';

export interface SalesPayment {
    id: string;
    business_id: string;
    sales_id: string;
    payment_number: string;
    payment_date: string;
    payment_method: PaymentMethod;
    amount: number | string;
    reference_number?: string | null;
    notes?: string | null;
    status: PaymentStatus;
    created_by_user_id: string;
    cancelled_by_user_id?: string | null;
    created_at: string;
    updated_at: string;
    cancelled_at?: string | null;
}

export interface SalesPaymentSummary {
    total_paid: number | string;
    remaining_amount: number | string;
    grand_total: number | string;
}

export interface SalesPaymentListResponse {
    items: SalesPayment[];
    summary: SalesPaymentSummary;
    page: number;
    page_size: number;
    total: number;
}

export interface CreateSalesPaymentRequest {
    payment_date?: string;
    payment_method: PaymentMethod;
    amount: number | string;
    reference_number?: string | null;
    notes?: string | null;
}
