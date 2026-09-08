import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BusinessMembership } from '@/types/businessMembership';
import type { SalesResponse, SalesLineResponse } from '@/types/sales';
import type { Product } from '@/types/product';
import type {
  SalesReturnResponse,
  SalesReturnLineCreateInput,
} from '@/types/salesReturn';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  FINALIZED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CANCELLED: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
};

export const SalesReturnDetail: React.FC = () => {
  const { businessId, returnId } = useParams<{ businessId: string; returnId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [salesReturn, setSalesReturn] = useState<SalesReturnResponse | null>(null);
  const [sales, setSales] = useState<SalesResponse | null>(null);
  const [salesLines, setSalesLines] = useState<SalesLineResponse[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const [isAddLineOpen, setIsAddLineOpen] = useState<boolean>(false);
  const [confirmAction, setConfirmAction] = useState<'finalize' | 'cancel' | 'deleteLine' | null>(null);
  const [lineToDelete, setLineToDelete] = useState<string | null>(null);
  const [formError, setFormError] = useState<string>('');

  const [lineForm, setLineForm] = useState<SalesReturnLineCreateInput>({
    sales_line_id: '',
    quantity: 1,
  });

  const isDraft = salesReturn?.status === 'DRAFT';
  const canManage = (myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN') && isDraft;

  const fetchDetail = useCallback(async () => {
    if (!businessId || !returnId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const retData = await apiClient.getSalesReturn(businessId, returnId);
      setSalesReturn(retData);

      const [salesData, prodData, membersData] = await Promise.all([
        apiClient.getSales(businessId, retData.sales_id).catch(() => null),
        apiClient.listProducts(businessId).catch(() => ({ items: [] })),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);
      setSales(salesData);
      if (salesData?.lines) setSalesLines(salesData.lines);
      setProducts(prodData.items || []);
      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat detail retur penjualan.';
      if (msg.toLowerCase().includes('unauthorized')) navigate('/login');
      else setServerError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, returnId, user, navigate]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 4000);
  };

  const handleAddLine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !returnId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: SalesReturnLineCreateInput = {
        sales_line_id: lineForm.sales_line_id,
        quantity: lineForm.quantity,
      };
      await apiClient.addSalesReturnLine(businessId, returnId, payload);
      setIsAddLineOpen(false);
      setLineForm({ sales_line_id: '', quantity: 1 });
      showSuccess('Line added successfully');
      await fetchDetail();
    } catch (err: any) {
      setFormError(err.message || 'Failed to add line');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteLine = async () => {
    if (!businessId || !returnId || !lineToDelete) return;
    try {
      await apiClient.deleteSalesReturnLine(businessId, returnId, lineToDelete);
      setConfirmAction(null);
      setLineToDelete(null);
      showSuccess('Line deleted');
      await fetchDetail();
    } catch (err: any) {
      setActionError(err.message);
    }
  };

  const handleFinalize = async () => {
    if (!businessId || !returnId) return;
    try {
      setIsSubmitting(true);
      await apiClient.finalizeSalesReturn(businessId, returnId);
      showSuccess('Return finalized successfully');
      await fetchDetail();
    } catch (err: any) {
      setActionError(err.message);
    } finally {
      setIsSubmitting(false);
      setConfirmAction(null);
    }
  };

  const handleCancel = async () => {
    if (!businessId || !returnId) return;
    try {
      setIsSubmitting(true);
      await apiClient.cancelSalesReturn(businessId, returnId);
      showSuccess('Return cancelled');
      await fetchDetail();
    } catch (err: any) {
      setActionError(err.message);
    } finally {
      setIsSubmitting(false);
      setConfirmAction(null);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {isLoading ? (
        <Loading />
      ) : serverError ? (
        <ErrorState message={serverError} />
      ) : salesReturn ? (
        <>
          {successMsg && (
            <div className="p-4 mb-4 text-sm text-emerald-700 bg-emerald-100 rounded-lg">{successMsg}</div>
          )}
          {actionError && (
            <div className="p-4 mb-4 text-sm text-rose-700 bg-rose-100 rounded-lg">{actionError}</div>
          )}

          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                {salesReturn.return_number}
                <span className={`px-2 py-1 rounded-md text-xs font-medium ${STATUS_COLORS[salesReturn.status]}`}>
                  {salesReturn.status}
                </span>
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Source Sales: {sales?.sales_number || salesReturn.sales_id}
              </p>
            </div>
            <div className="flex gap-2">
              <Link to={`/businesses/${businessId}/sales/${salesReturn.sales_id}`}>
                <Button variant="secondary">View Sales</Button>
              </Link>
              {canManage && (
                <>
                  <Button onClick={() => setIsAddLineOpen(true)}>Add Line</Button>
                  <Button 
                    onClick={() => setConfirmAction('finalize')} 
                    variant="primary"
                    disabled={isSubmitting || !salesReturn.lines.length}
                  >
                    Finalize
                  </Button>
                  <Button onClick={() => setConfirmAction('cancel')} variant="danger">
                    Cancel
                  </Button>
                </>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <div className="p-6 space-y-4">
                <h2 className="text-lg font-semibold border-b pb-2">Return Details</h2>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div><span className="font-medium text-gray-500">Return Number:</span> {salesReturn.return_number}</div>
                  <div><span className="font-medium text-gray-500">Status:</span> {salesReturn.status}</div>
                  <div><span className="font-medium text-gray-500">Created At:</span> {new Date(salesReturn.created_at).toLocaleString()}</div>
                  <div><span className="font-medium text-gray-500">Created By:</span> {salesReturn.created_by_user_id}</div>
                  {salesReturn.finalized_at && <div><span className="font-medium text-gray-500">Finalized At:</span> {new Date(salesReturn.finalized_at).toLocaleString()}</div>}
                  {salesReturn.cancelled_at && <div><span className="font-medium text-gray-500">Cancelled At:</span> {new Date(salesReturn.cancelled_at).toLocaleString()}</div>}
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-6 space-y-4">
                <h2 className="text-lg font-semibold border-b pb-2">Totals</h2>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="text-right"><span className="font-medium text-gray-500">Subtotal:</span></div>
                  <div className="font-medium">IDR {Number(salesReturn.subtotal).toLocaleString()}</div>
                  <div className="text-right"><span className="font-medium text-gray-500">Discount:</span></div>
                  <div className="font-medium text-rose-600">- IDR {Number(salesReturn.discount_total).toLocaleString()}</div>
                  <div className="text-right"><span className="font-medium text-gray-500">Tax:</span></div>
                  <div className="font-medium">+ IDR {Number(salesReturn.tax_total).toLocaleString()}</div>
                  <div className="text-right border-t pt-2"><span className="font-bold">Grand Total:</span></div>
                  <div className="font-bold text-lg border-t pt-2">IDR {Number(salesReturn.grand_total).toLocaleString()}</div>
                </div>
              </div>
            </Card>
          </div>

          <Card>
            <div className="p-6">
              <h2 className="text-lg font-semibold border-b pb-2 mb-4">Return Lines</h2>
              {salesReturn.lines.length === 0 ? (
                <div className="text-center py-8 text-gray-500">No lines added yet.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 border-b">
                      <tr>
                        <th className="px-4 py-3">Source Line ID</th>
                        <th className="px-4 py-3">Product</th>
                        <th className="px-4 py-3 text-right">Qty</th>
                        <th className="px-4 py-3 text-right">Unit Price</th>
                        <th className="px-4 py-3 text-right">Total</th>
                        {canManage && <th className="px-4 py-3">Action</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {salesReturn.lines.map((line) => {
                        const product = products.find((p) => p.id === line.product_id);
                        return (
                          <tr key={line.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                            <td className="px-4 py-3 font-mono text-xs">{line.sales_line_id.substring(0, 8)}...</td>
                            <td className="px-4 py-3">{product?.name || line.product_id}</td>
                            <td className="px-4 py-3 text-right">{line.quantity}</td>
                            <td className="px-4 py-3 text-right">IDR {Number(line.unit_price).toLocaleString()}</td>
                            <td className="px-4 py-3 text-right">IDR {Number(line.line_total).toLocaleString()}</td>
                            {canManage && (
                              <td className="px-4 py-3">
                                <Button 
                                  size="sm" 
                                  variant="ghost" 
                                  className="text-rose-600 hover:text-rose-700"
                                  onClick={() => { setLineToDelete(line.id); setConfirmAction('deleteLine'); }}
                                >
                                  Delete
                                </Button>
                              </td>
                            )}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Card>

          {confirmAction === 'finalize' && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <Card className="w-full max-w-md p-6 space-y-4">
                <h3 className="text-lg font-bold">Confirm Finalize</h3>
                <p>Are you sure you want to finalize this return? This will increase inventory stock and cannot be undone.</p>
                {actionError && <p className="text-rose-600 text-sm">{actionError}</p>}
                <div className="flex justify-end gap-2">
                  <Button variant="secondary" onClick={() => { setConfirmAction(null); setActionError(''); }}>No, cancel</Button>
                  <Button onClick={handleFinalize} disabled={isSubmitting}>Yes, finalize</Button>
                </div>
              </Card>
            </div>
          )}

          {confirmAction === 'cancel' && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <Card className="w-full max-w-md p-6 space-y-4">
                <h3 className="text-lg font-bold">Confirm Cancel Return</h3>
                <p>Are you sure you want to cancel this draft return?</p>
                {actionError && <p className="text-rose-600 text-sm">{actionError}</p>}
                <div className="flex justify-end gap-2">
                  <Button variant="secondary" onClick={() => { setConfirmAction(null); setActionError(''); }}>No, keep it</Button>
                  <Button variant="danger" onClick={handleCancel} disabled={isSubmitting}>Yes, cancel return</Button>
                </div>
              </Card>
            </div>
          )}

          {confirmAction === 'deleteLine' && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <Card className="w-full max-w-md p-6 space-y-4">
                <h3 className="text-lg font-bold">Confirm Delete Line</h3>
                <p>Are you sure you want to delete this return line?</p>
                {actionError && <p className="text-rose-600 text-sm">{actionError}</p>}
                <div className="flex justify-end gap-2">
                  <Button variant="secondary" onClick={() => { setConfirmAction(null); setLineToDelete(null); setActionError(''); }}>No</Button>
                  <Button variant="danger" onClick={handleDeleteLine} disabled={isSubmitting}>Yes, delete line</Button>
                </div>
              </Card>
            </div>
          )}

          {isAddLineOpen && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <Card className="w-full max-w-lg p-6 space-y-4">
                <h3 className="text-lg font-bold">Add Return Line</h3>
                <form onSubmit={handleAddLine} className="space-y-4">
                  {formError && <p className="text-rose-600 text-sm">{formError}</p>}
                  
                  <div className="space-y-1">
                    <label className="block text-sm font-medium">Source Sales Line</label>
                    <select
                      value={lineForm.sales_line_id}
                      onChange={(e) => setLineForm({ ...lineForm, sales_line_id: e.target.value })}
                      className="w-full border rounded p-2 dark:bg-gray-800 dark:border-gray-600"
                      required
                    >
                      <option value="">Select a line...</option>
                      {salesLines.map((sl) => {
                        const prod = products.find((p) => p.id === sl.product_id);
                        return (
                          <option key={sl.id} value={sl.id}>
                            {prod?.name || sl.product_id} - Qty: {sl.quantity} - Price: IDR {Number(sl.unit_price).toLocaleString()}
                          </option>
                        );
                      })}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="block text-sm font-medium">Quantity to Return</label>
                    <Input
                      type="number"
                      min="1"
                      step="1"
                      value={lineForm.quantity}
                      onChange={(e) => setLineForm({ ...lineForm, quantity: Number(e.target.value) })}
                      required
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-4">
                    <Button type="button" variant="secondary" onClick={() => { setIsAddLineOpen(false); setFormError(''); }}>Cancel</Button>
                    <Button type="submit" disabled={isSubmitting || !lineForm.sales_line_id}>Add Line</Button>
                  </div>
                </form>
              </Card>
            </div>
          )}
        </>
      ) : (
        <EmptyState title="Return Not Found" description="The requested sales return could not be found." />
      )}
    </div>
  );
};
