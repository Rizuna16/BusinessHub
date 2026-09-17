export interface PaymentAnalyticsSummaryResponse {
  date_from: string;
  date_to: string;
  gross_recorded: number | string;
  customer_in_total: number | string;
  supplier_out_total: number | string;
  net_payment_flow: number | string;
  voided_count: number;
  voided_amount: number | string;
  payment_count: number;
  average_payment_value: number | string;
}

export interface PaymentDirectionBreakdownItem {
  direction: string;
  amount: number | string;
  payment_count: number;
}

export interface PaymentAnalyticsByDirectionResponse {
  date_from: string;
  date_to: string;
  gross_recorded: number | string;
  payment_count: number;
  directions: PaymentDirectionBreakdownItem[];
}

export interface PaymentMethodBreakdownItem {
  payment_method: string;
  amount: number | string;
  payment_count: number;
}

export interface PaymentAnalyticsByMethodResponse {
  date_from: string;
  date_to: string;
  gross_recorded: number | string;
  payment_count: number;
  methods: PaymentMethodBreakdownItem[];
}
