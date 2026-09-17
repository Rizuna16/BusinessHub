import React, { useEffect, useState } from 'react';
import type { PlatformSubscription, SubscriptionOverrideInput, SubscriptionPlan, PlanCreateInput, PlanUpdateInput, PaymentAttemptResponse, BillingPeriod } from '../../types/platform';
import { platformApiClient } from '../../services/platformApiClient';

export const PlatformSubscriptionsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'subscriptions' | 'plans' | 'checkout'>('subscriptions');
  const [subscriptions, setSubscriptions] = useState<PlatformSubscription[]>([]);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [businessFilter, setBusinessFilter] = useState('');

  const [selectedSub, setSelectedSub] = useState<PlatformSubscription | null>(null);
  const [overrideAction, setOverrideAction] = useState<'EXTEND' | 'SET_STATUS'>('EXTEND');
  const [extendDays, setExtendDays] = useState<number>(30);
  const [newStatus, setNewStatus] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideLoading, setOverrideLoading] = useState(false);
  const [overrideError, setOverrideError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Plan Management State
  const [planMode, setPlanMode] = useState<'list' | 'create' | 'edit'>('list');
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlan | null>(null);
  const [planFormValues, setPlanFormValues] = useState<PlanCreateInput>({
    name: '',
    description: '',
    billing_interval: 'MONTHLY',
    price: '50000.00',
    currency: 'IDR',
  });
  const [planLoading, setPlanLoading] = useState(false);

  // Checkout & Manual Transfer Verification State
  const [selectedCheckoutSubId, setSelectedCheckoutSubId] = useState('');
  const [billingPeriods, setBillingPeriods] = useState<BillingPeriod[]>([]);
  const [selectedBpId, setSelectedBpId] = useState('');
  const [checkoutResult, setCheckoutResult] = useState<PaymentAttemptResponse | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [paymentReference, setPaymentReference] = useState('');
  const [verificationNote, setVerificationNote] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);

  const loadSubscriptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await platformApiClient.listSubscriptions(statusFilter || undefined, businessFilter || undefined);
      if (Array.isArray(data)) {
        setSubscriptions(data);
      } else {
        setSubscriptions([]);
      }
    } catch (err: any) {
      setError(err.message || 'Gagal memuat data langganan.');
      setSubscriptions([]);
    } finally {
      setLoading(false);
    }
  };

  const loadPlans = async () => {
    try {
      const data = await platformApiClient.listPlans();
      if (Array.isArray(data)) {
        setPlans(data);
      } else {
        setPlans([]);
      }
    } catch (err: any) {
      console.error(err.message);
      setPlans([]);
    }
  };

  useEffect(() => {
    if (activeTab === 'subscriptions') loadSubscriptions();
    if (activeTab === 'plans') loadPlans();
    if (activeTab === 'checkout') loadSubscriptions();
  }, [activeTab, statusFilter, businessFilter]);

  useEffect(() => {
    if (selectedCheckoutSubId) {
      platformApiClient.getBillingPeriods(selectedCheckoutSubId).then(bps => {
        if (Array.isArray(bps)) {
          setBillingPeriods(bps);
          if (bps.length > 0) setSelectedBpId(bps[0].id);
        } else {
          setBillingPeriods([]);
          setSelectedBpId('');
        }
      }).catch(err => {
        console.error(err);
        setBillingPeriods([]);
        setSelectedBpId('');
      });
    } else {
      setBillingPeriods([]);
      setSelectedBpId('');
    }
  }, [selectedCheckoutSubId]);

  const handleOverride = async () => {
    if (!selectedSub || !overrideReason) return;
    setOverrideLoading(true);
    setOverrideError(null);
    setSuccessMessage(null);
    
    try {
      const payload: SubscriptionOverrideInput = {
        action: overrideAction,
        reason: overrideReason,
      };
      
      if (overrideAction === 'EXTEND') {
        payload.extend_days = extendDays;
      } else if (overrideAction === 'SET_STATUS') {
        payload.status = newStatus as any;
      }
      
      await platformApiClient.overrideSubscription(selectedSub.id, payload);
      setSelectedSub(null);
      setOverrideReason('');
      setSuccessMessage('Subscription overridden successfully.');
      await loadSubscriptions();
    } catch (err: any) {
      setOverrideError(err.message || 'Override failed');
    } finally {
      setOverrideLoading(false);
    }
  };

  const handleSavePlan = async () => {
    setPlanLoading(true);
    setError(null);
    try {
      if (planMode === 'create') {
        await platformApiClient.createPlan(planFormValues);
        setSuccessMessage('Plan created successfully.');
      } else if (planMode === 'edit' && selectedPlan) {
        await platformApiClient.updatePlan(selectedPlan.id, planFormValues as PlanUpdateInput);
        setSuccessMessage('Plan updated successfully.');
      }
      setPlanMode('list');
      await loadPlans();
    } catch (err: any) {
      setError(err.message || 'Failed to save plan.');
    } finally {
      setPlanLoading(false);
    }
  };

  const handleTogglePlanStatus = async (planId: string, isCurrentlyActive: boolean) => {
    setError(null);
    try {
      if (isCurrentlyActive) {
        await platformApiClient.deactivatePlan(planId);
        setSuccessMessage('Plan deactivated successfully.');
      } else {
        await platformApiClient.activatePlan(planId);
        setSuccessMessage('Plan activated successfully.');
      }
      await loadPlans();
    } catch (err: any) {
      setError(err.message || 'Failed to toggle plan status.');
    }
  };

  const handleCheckout = async () => {
    if (!selectedCheckoutSubId) return;
    setCheckoutLoading(true);
    setCheckoutResult(null);
    setError(null);
    try {
      const result = await platformApiClient.createCheckoutSession(selectedCheckoutSubId);
      setCheckoutResult(result);
      setSuccessMessage('Manual bank transfer checkout initiated. Provide payment reference for verification.');
    } catch (err: any) {
      setError(err.message || 'Failed to initiate checkout.');
    } finally {
      setCheckoutLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!selectedCheckoutSubId || !selectedBpId || !checkoutResult || !paymentReference) return;
    setVerifyLoading(true);
    setError(null);
    try {
      const res = await platformApiClient.verifyManualPayment(
        selectedCheckoutSubId,
        selectedBpId,
        checkoutResult.id,
        { payment_reference: paymentReference, verification_note: verificationNote }
      );
      setCheckoutResult(res);
      setSuccessMessage('Manual bank transfer verified successfully by Super Admin.');
      await loadSubscriptions();
    } catch (err: any) {
      setError(err.message || 'Verification failed.');
    } finally {
      setVerifyLoading(false);
    }
  };

  const statusBadge = (statusStr: string) => {
    const styles: Record<string, string> = {
      ACTIVE: 'bg-green-100 text-green-800',
      PAST_DUE: 'bg-orange-100 text-orange-800',
      EXPIRED: 'bg-red-100 text-red-800',
      CANCELLED: 'bg-slate-100 text-slate-800',
      SUSPENDED: 'bg-yellow-100 text-yellow-800',
      PENDING: 'bg-blue-100 text-blue-800',
      PROCESSING: 'bg-purple-100 text-purple-800',
      SUCCESS: 'bg-green-100 text-green-800',
      INACTIVE: 'bg-slate-100 text-slate-500'
    };
    return (
      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${styles[statusStr] || 'bg-gray-100 text-gray-800'}`}>
        {statusStr}
      </span>
    );
  };

  const safeSubscriptions = Array.isArray(subscriptions) ? subscriptions : [];
  const safePlans = Array.isArray(plans) ? plans : [];
  const safeBillingPeriods = Array.isArray(billingPeriods) ? billingPeriods : [];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Subscription & Billing Management</h1>

      <div className="flex space-x-4 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('subscriptions')}
          className={`px-4 py-2 font-medium ${activeTab === 'subscriptions' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-slate-500 hover:text-slate-700'}`}
        >
          Subscriptions
        </button>
        <button
          onClick={() => setActiveTab('plans')}
          className={`px-4 py-2 font-medium ${activeTab === 'plans' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-slate-500 hover:text-slate-700'}`}
        >
          Plan Management
        </button>
        <button
          onClick={() => setActiveTab('checkout')}
          className={`px-4 py-2 font-medium ${activeTab === 'checkout' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-slate-500 hover:text-slate-700'}`}
        >
          Manual Bank Transfer & Verification
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-md border border-red-200">{error}</div>
      )}

      {successMessage && (
        <div className="p-4 bg-green-50 text-green-700 rounded-md border border-green-200">{successMessage}</div>
      )}

      {activeTab === 'subscriptions' && (
        <>
          <div className="flex space-x-4">
            <input
              type="text"
              placeholder="Filter by Business ID..."
              value={businessFilter}
              onChange={(e) => setBusinessFilter(e.target.value)}
              className="flex-1 px-4 py-2 border border-slate-300 rounded-md"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 border border-slate-300 rounded-md"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="PAST_DUE">Past Due</option>
              <option value="EXPIRED">Expired</option>
              <option value="CANCELLED">Cancelled</option>
              <option value="SUSPENDED">Suspended</option>
            </select>
          </div>

          {loading ? (
            <div className="flex justify-center py-12 text-slate-500">Loading subscriptions...</div>
          ) : (
            <div className="bg-white shadow rounded-lg overflow-hidden border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Business ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Plan</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Amount</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Period End</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {safeSubscriptions.map((sub) => (
                    <tr key={sub.id} className="hover:bg-slate-50">
                      <td className="px-4 py-4 whitespace-nowrap text-sm font-mono text-slate-700">
                        {sub.business_id ? `${sub.business_id.substring(0, 8)}...` : '-'}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-900">{sub.plan_name || '-'}</td>
                      <td className="px-4 py-4 whitespace-nowrap">{statusBadge(sub.status || 'UNKNOWN')}</td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-900">
                        Rp {Number(sub.price || 0).toLocaleString('id-ID')}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-900">
                        {sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString() : '-'}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium flex space-x-2 justify-end">
                        <button
                          onClick={() => platformApiClient.renewSubscription(sub.id).then(() => {
                            setSuccessMessage('Subscription renewed successfully.');
                            loadSubscriptions();
                          }).catch(err => setError(err.message || 'Renewal failed.'))}
                          className="text-green-600 hover:text-green-900 mr-3"
                        >
                          Renew
                        </button>
                        <button
                          onClick={() => setSelectedSub(sub)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Override
                        </button>
                      </td>
                    </tr>
                  ))}
                  {safeSubscriptions.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center text-slate-500">No subscriptions found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {activeTab === 'plans' && (
        <div className="space-y-4">
          {planMode === 'list' && (
            <>
              <button
                onClick={() => { setPlanMode('create'); setSelectedPlan(null); setPlanFormValues({ name: '', description: '', billing_interval: 'MONTHLY', price: '50000.00', currency: 'IDR' }); }}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Create New Plan
              </button>
              <div className="bg-white shadow rounded-lg overflow-hidden border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Name</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Price (IDR)</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Interval</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {safePlans.map((plan) => (
                      <tr key={plan.id} className="hover:bg-slate-50">
                        <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{plan.name}</td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-900">Rp {Number(plan.price || 0).toLocaleString('id-ID')}</td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-900">{plan.billing_interval}</td>
                        <td className="px-4 py-4 whitespace-nowrap">{statusBadge(plan.is_active ? 'ACTIVE' : 'INACTIVE')}</td>
                        <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium flex justify-end space-x-2">
                          <button
                            onClick={() => { setPlanMode('edit'); setSelectedPlan(plan); setPlanFormValues({ name: plan.name, description: plan.description, price: String(plan.price), billing_interval: plan.billing_interval, currency: plan.currency }); }}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleTogglePlanStatus(plan.id, plan.is_active)}
                            className={`px-2 py-1 text-xs rounded ${plan.is_active ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-green-100 text-green-700 hover:bg-green-200'}`}
                          >
                            {plan.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        </td>
                      </tr>
                    ))}
                    {safePlans.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-6 py-12 text-center text-slate-500">No plans found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {(planMode === 'create' || planMode === 'edit') && (
            <div className="bg-white shadow rounded-lg p-6 border border-slate-200 max-w-lg">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">{planMode === 'create' ? 'Create New Plan' : 'Edit Plan'}</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Plan Name</label>
                  <input
                    type="text"
                    value={planFormValues.name}
                    onChange={(e) => setPlanFormValues({ ...planFormValues, name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md"
                    placeholder="e.g. Business Pro"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                  <input
                    type="text"
                    value={planFormValues.description}
                    onChange={(e) => setPlanFormValues({ ...planFormValues, description: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Price (IDR)</label>
                    <input
                      type="number"
                      value={planFormValues.price}
                      onChange={(e) => setPlanFormValues({ ...planFormValues, price: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Billing Interval</label>
                    <select
                      value={planFormValues.billing_interval}
                      onChange={(e) => setPlanFormValues({ ...planFormValues, billing_interval: e.target.value as any })}
                      className="w-full px-3 py-2 border border-slate-300 rounded-md"
                    >
                      <option value="MONTHLY">MONTHLY</option>
                      <option value="YEARLY">YEARLY</option>
                    </select>
                  </div>
                </div>
                <div className="flex space-x-4 pt-4">
                  <button
                    onClick={handleSavePlan}
                    disabled={planLoading || !planFormValues.name}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {planLoading ? 'Saving...' : 'Save Plan'}
                  </button>
                  <button
                    onClick={() => setPlanMode('list')}
                    className="px-4 py-2 bg-slate-200 text-slate-800 rounded-md hover:bg-slate-300"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'checkout' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white shadow rounded-lg p-6 border border-slate-200 space-y-4">
            <h3 className="text-lg font-semibold text-slate-900">Initiate Manual Bank Transfer Checkout</h3>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Select Subscription</label>
              <select
                value={selectedCheckoutSubId}
                onChange={(e) => setSelectedCheckoutSubId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-md"
              >
                <option value="">Select subscription...</option>
                {safeSubscriptions.map(s => <option key={s.id} value={s.id}>Subscription {s.id ? s.id.substring(0, 8) : ''}... ({s.plan_name})</option>)}
              </select>
            </div>
            <button
              onClick={handleCheckout}
              disabled={checkoutLoading || !selectedCheckoutSubId}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {checkoutLoading ? 'Processing...' : 'Generate Bank Transfer Order'}
            </button>

            {checkoutResult && (
              <div className="mt-4 p-4 bg-slate-50 rounded-md border border-slate-200 space-y-2 text-sm">
                <div className="font-semibold text-slate-900">Payment Attempt Created</div>
                <div className="flex justify-between"><span className="text-slate-500">Order ID:</span><span className="font-mono">{checkoutResult.provider_order_id}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Amount:</span><span>Rp {Number(checkoutResult.amount || 0).toLocaleString('id-ID')}</span></div>
                <div className="flex justify-between items-center"><span className="text-slate-500">Status:</span>{statusBadge(checkoutResult.status || 'CREATED')}</div>
              </div>
            )}
          </div>

          <div className="bg-white shadow rounded-lg p-6 border border-slate-200 space-y-4">
            <h3 className="text-lg font-semibold text-slate-900">Super Admin Payment Verification</h3>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Select Billing Period</label>
              <select
                value={selectedBpId}
                onChange={(e) => setSelectedBpId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-md"
              >
                <option value="">Select billing period...</option>
                {safeBillingPeriods.map(bp => <option key={bp.id} value={bp.id}>Period {bp.id ? bp.id.substring(0, 8) : ''}... (Rp {Number(bp.price_snapshot || 0).toLocaleString('id-ID')} - {bp.payment_status})</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Bank Transfer Reference / Receipt Number *</label>
              <input
                type="text"
                value={paymentReference}
                onChange={(e) => setPaymentReference(e.target.value)}
                placeholder="e.g. TRX-BCA-987654321"
                className="w-full px-3 py-2 border border-slate-300 rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Verification Note</label>
              <input
                type="text"
                value={verificationNote}
                onChange={(e) => setVerificationNote(e.target.value)}
                placeholder="e.g. Verified against BCA statement #1234"
                className="w-full px-3 py-2 border border-slate-300 rounded-md"
              />
            </div>
            <button
              onClick={handleVerify}
              disabled={verifyLoading || !selectedCheckoutSubId || !selectedBpId || !checkoutResult || !paymentReference}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              {verifyLoading ? 'Verifying...' : 'Verify & Approve Payment'}
            </button>
          </div>
        </div>
      )}

      {selectedSub && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">Override Subscription</h3>
            {overrideError && (
              <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">{overrideError}</div>
            )}
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Action</label>
                <select
                  value={overrideAction}
                  onChange={(e) => setOverrideAction(e.target.value as any)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md"
                >
                  <option value="EXTEND">Extend Period</option>
                  <option value="SET_STATUS">Set Status</option>
                </select>
              </div>

              {overrideAction === 'EXTEND' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Extend By (Days)</label>
                  <input
                    type="number"
                    value={extendDays}
                    onChange={(e) => setExtendDays(parseInt(e.target.value) || 0)}
                    min={1}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md"
                  />
                </div>
              )}

              {overrideAction === 'SET_STATUS' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">New Status</label>
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md"
                  >
                    <option value="">Select Status</option>
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="SUSPENDED">SUSPENDED</option>
                    <option value="CANCELLED">CANCELLED</option>
                    <option value="PAST_DUE">PAST_DUE</option>
                    <option value="EXPIRED">EXPIRED</option>
                  </select>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Reason *</label>
                <input
                  type="text"
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Provide a reason..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-md"
                />
              </div>

              <div className="flex space-x-4 pt-4">
                <button
                  onClick={handleOverride}
                  disabled={overrideLoading || !overrideReason}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {overrideLoading ? 'Processing...' : 'Confirm Override'}
                </button>
                <button
                  onClick={() => setSelectedSub(null)}
                  className="px-4 py-2 bg-slate-200 text-slate-800 rounded-md hover:bg-slate-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlatformSubscriptionsPage;
