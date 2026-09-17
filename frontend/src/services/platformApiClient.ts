import type {
  PlatformDashboard,
  PlatformUser,
  PlatformBusiness,
  PlatformBusinessMember,
  PlatformSubscription,
  SubscriptionOverrideInput,
  PlatformAuditLog,
  BusinessActionInput,
  AuditLogFilters,
  SubscriptionPlan,
  PlanCreateInput,
  PlanUpdateInput,
  PaymentAttemptResponse,
  BillingPeriod,
  VerifyPaymentInput,
} from '../types/platform';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class PlatformApiClient {
  private getToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}/platform${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMessage = data.message || data.detail || (data.errors && data.errors[0]) || 'Platform API error occurred';
      throw new Error(errorMessage);
    }

    return (data.data !== undefined ? data.data : data) as T;
  }

  public async getDashboard(): Promise<PlatformDashboard> {
    return this.request<PlatformDashboard>('/dashboard');
  }

  public async listBusinesses(status?: string, search?: string): Promise<PlatformBusiness[]> {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (search) params.set('search', search);
    const qs = params.toString();
    return this.request<PlatformBusiness[]>(`/businesses${qs ? `?${qs}` : ''}`);
  }

  public async getBusinessDetail(businessId: string): Promise<PlatformBusiness> {
    return this.request<PlatformBusiness>(`/businesses/${businessId}`);
  }

  public async suspendBusiness(businessId: string, payload: BusinessActionInput): Promise<PlatformBusiness> {
    return this.request<PlatformBusiness>(`/businesses/${businessId}/suspend`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async activateBusiness(businessId: string, payload: BusinessActionInput): Promise<PlatformBusiness> {
    return this.request<PlatformBusiness>(`/businesses/${businessId}/activate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async archiveBusiness(businessId: string, payload: BusinessActionInput): Promise<PlatformBusiness> {
    return this.request<PlatformBusiness>(`/businesses/${businessId}/archive`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async listBusinessMembers(businessId: string): Promise<PlatformBusinessMember[]> {
    return this.request<PlatformBusinessMember[]>(`/businesses/${businessId}/members`);
  }

  public async listUsers(search?: string): Promise<PlatformUser[]> {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    const qs = params.toString();
    return this.request<PlatformUser[]>(`/users${qs ? `?${qs}` : ''}`);
  }

  public async listAuditLogs(filters?: AuditLogFilters): Promise<PlatformAuditLog[]> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.actor_id) params.set('actor_id', filters.actor_id);
      if (filters.action) params.set('action', filters.action);
      if (filters.target_type) params.set('target_type', filters.target_type);
      if (filters.from_date) params.set('from_date', filters.from_date);
      if (filters.to_date) params.set('to_date', filters.to_date);
    }
    const qs = params.toString();
    return this.request<PlatformAuditLog[]>(`/audit-logs${qs ? `?${qs}` : ''}`);
  }

  public async listSubscriptions(status?: string, businessId?: string): Promise<PlatformSubscription[]> {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (businessId) params.set('business_id', businessId);
    const qs = params.toString();
    return this.request<PlatformSubscription[]>(`/subscriptions${qs ? `?${qs}` : ''}`);
  }

  public async getSubscription(subscriptionId: string): Promise<PlatformSubscription> {
    return this.request<PlatformSubscription>(`/subscriptions/${subscriptionId}`);
  }

  public async getBillingPeriods(subscriptionId: string): Promise<BillingPeriod[]> {
    return this.request<BillingPeriod[]>(`/subscriptions/${subscriptionId}/billing-periods`);
  }

  public async overrideSubscription(
    subscriptionId: string,
    payload: SubscriptionOverrideInput
  ): Promise<PlatformSubscription> {
    return this.request<PlatformSubscription>(`/subscriptions/${subscriptionId}/override`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async listPlans(): Promise<SubscriptionPlan[]> {
    return this.request<SubscriptionPlan[]>('/plans');
  }

  public async createPlan(payload: PlanCreateInput): Promise<SubscriptionPlan> {
    return this.request<SubscriptionPlan>('/plans', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async updatePlan(planId: string, payload: PlanUpdateInput): Promise<SubscriptionPlan> {
    return this.request<SubscriptionPlan>(`/plans/${planId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  public async activatePlan(planId: string): Promise<SubscriptionPlan> {
    return this.request<SubscriptionPlan>(`/plans/${planId}/activate`, {
      method: 'POST',
    });
  }

  public async deactivatePlan(planId: string): Promise<SubscriptionPlan> {
    return this.request<SubscriptionPlan>(`/plans/${planId}/deactivate`, {
      method: 'POST',
    });
  }

  public async createCheckoutSession(subscriptionId: string): Promise<PaymentAttemptResponse> {
    return this.request<PaymentAttemptResponse>(`/subscriptions/${subscriptionId}/checkout`, {
      method: 'POST',
    });
  }

  public async renewSubscription(subscriptionId: string): Promise<PlatformSubscription> {
    return this.request<PlatformSubscription>(`/subscriptions/${subscriptionId}/renew`, {
      method: 'POST',
    });
  }

  public async verifyManualPayment(
    subscriptionId: string,
    billingPeriodId: string,
    paymentAttemptId: string,
    payload: VerifyPaymentInput
  ): Promise<PaymentAttemptResponse> {
    return this.request<PaymentAttemptResponse>(
      `/subscriptions/${subscriptionId}/billing-periods/${billingPeriodId}/payment-attempts/${paymentAttemptId}/verify`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  }
}

export const platformApiClient = new PlatformApiClient();
