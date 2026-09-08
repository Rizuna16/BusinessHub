import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { SalesReturnResponse } from '@/types/salesReturn';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  FINALIZED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CANCELLED: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
};

export const SalesReturns: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [returns, setReturns] = useState<SalesReturnResponse[]>([]);
  const [totalReturns, setTotalReturns] = useState<number>(0);
  const [page, setPage] = useState<number>(1);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchReturns = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const [resData] = await Promise.all([
        apiClient.listSalesReturns(businessId, { page, page_size: 20 }),
      ]);
      setReturns(resData.items || []);
      setTotalReturns(resData.total || 0);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat data retur penjualan.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, page]);

  useEffect(() => { fetchReturns(); }, [fetchReturns]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Sales Returns</h1>
        <Link to={`/businesses/${businessId}/sales`}>
          <Button variant="secondary">Back to Sales</Button>
        </Link>
      </div>

      {isLoading ? (
        <Loading />
      ) : serverError ? (
        <ErrorState message={serverError} />
      ) : (
        <>
          {returns.length === 0 ? (
            <EmptyState title="No Sales Returns" description="There are no sales returns recorded yet." />
          ) : (
            <Card>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 border-b">
                    <tr>
                      <th className="px-6 py-3">Return Number</th>
                      <th className="px-6 py-3">Sales ID</th>
                      <th className="px-6 py-3">Date</th>
                      <th className="px-6 py-3">Grand Total</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {returns.map((ret) => (
                      <tr key={ret.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-6 py-4 font-medium">{ret.return_number}</td>
                        <td className="px-6 py-4">{ret.sales_id.substring(0, 8)}...</td>
                        <td className="px-6 py-4">{new Date(ret.created_at).toLocaleDateString()}</td>
                        <td className="px-6 py-4">IDR {Number(ret.grand_total).toLocaleString()}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 rounded-md text-xs font-medium ${STATUS_COLORS[ret.status]}`}>
                            {ret.status}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <Link to={`/businesses/${businessId}/sales-returns/${ret.id}`}>
                            <Button size="sm" variant="ghost">View</Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="p-4 flex justify-between items-center text-sm text-gray-500">
                <span>Total: {totalReturns}</span>
                <div className="flex gap-2">
                  <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>Prev</Button>
                  <span>Page {page}</span>
                  <Button size="sm" variant="secondary" disabled={returns.length < 20} onClick={() => setPage(p => p + 1)}>Next</Button>
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
};
