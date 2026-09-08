import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Payment } from '@/types/payment';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';

const STATUS_COLORS: Record<string, string> = {
  RECORDED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  VOIDED: 'bg-gray-100 text-gray-500 border border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700 line-through',
};

export const PaymentDetail: React.FC = () => {
  const { businessId, paymentId } = useParams<{ businessId: string; paymentId: string }>();

  const [payment, setPayment] = useState<Payment | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isVoiding, setIsVoiding] = useState<boolean>(false);
  const [serverError, setServerError] = useState<string>('');

  const fetchDetail = useCallback(async () => {
    if (!businessId || !paymentId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const data = await apiClient.getPaymentById(businessId, paymentId);
      setPayment(data);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat detail pembayaran.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, paymentId]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const handleVoid = async () => {
    if (!businessId || !paymentId || !confirm('Anda yakin ingin membatalkan transaksi ini? Pembatalan akan mengembalikan saldo kas.')) return;
    setIsVoiding(true);
    try {
      const updated = await apiClient.voidPayment(businessId, paymentId);
      setPayment(updated);
    } catch (err: any) {
      alert('Gagal membatalkan pembayaran: ' + (err.message || 'Unknown error'));
    } finally {
      setIsVoiding(false);
    }
  };

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  if (isLoading) return <div className="p-6"><Loading /></div>;
  if (serverError || !payment) return <div className="p-6"><ErrorState message={serverError || 'Payment not found'} onRetry={fetchDetail} /></div>;

  const targetUrl = payment.target_type === 'SALES'
    ? `/businesses/${businessId}/sales/${payment.target_id}`
    : `/businesses/${businessId}/purchases/${payment.target_id}`;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            Pembayaran: {payment.payment_number}
            <span className={`px-2.5 py-0.5 text-xs rounded-full font-semibold ${STATUS_COLORS[payment.status] || ''}`}>
              {payment.status}
            </span>
          </h1>
          <p className="text-sm text-gray-500">
            Tanggal Pembayaran: {new Date(payment.payment_date).toLocaleDateString('id-ID')}
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="danger" 
            onClick={handleVoid} 
            disabled={isVoiding || payment.status === 'VOIDED'}
          >
            {isVoiding ? 'Membatalkan...' : 'Batalkan Pembayaran'}
          </Button>
          <Link to={targetUrl}>
            <Button variant="secondary">Lihat {payment.target_type === 'SALES' ? 'Sales' : 'Purchase'}</Button>
          </Link>
          <Link to={`/businesses/${businessId}/payments`}>
            <Button variant="secondary">Kembali</Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <h3 className="font-semibold text-sm mb-3">Detail Transaksi</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">ID Pembayaran:</span>
              <span className="font-mono">{payment.id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">No. Pembayaran:</span>
              <span className="font-medium">{payment.payment_number}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Arah:</span>
              <span className="font-medium">{payment.direction === 'CUSTOMER_IN' ? 'Penerimaan Pelanggan' : 'Pembayaran Supplier'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Target Tipe:</span>
              <span className="font-medium">{payment.target_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Referensi:</span>
              <span className="font-medium">{payment.reference_number || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Catatan:</span>
              <span className="font-medium">{payment.notes || '-'}</span>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="font-semibold text-sm mb-3">Rincian Finansial</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between font-semibold text-base border-b pb-2">
              <span>Nominal Pembayaran ({payment.currency}):</span>
              <span className={payment.direction === 'CUSTOMER_IN' ? 'text-emerald-600' : 'text-rose-600'}>
                {payment.direction === 'CUSTOMER_IN' ? '+' : '-'} Rp {formatCurrency(payment.amount)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Metode Pembayaran:</span>
              <span className="font-medium">{payment.payment_method.replace('_', ' ')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Akun Kas:</span>
              <span className="font-medium">{payment.cash_account_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Dibuat Oleh:</span>
              <span className="font-mono text-xs">{payment.created_by_user_id}</span>
            </div>
            {payment.status === 'VOIDED' && (
              <>
                <div className="flex justify-between text-red-500">
                  <span>Dibatalkan Oleh:</span>
                  <span className="font-mono text-xs">{payment.voided_by_user_id}</span>
                </div>
                <div className="flex justify-between text-red-500">
                  <span>Waktu Pembatalan:</span>
                  <span>{payment.voided_at ? new Date(payment.voided_at).toLocaleString() : '-'}</span>
                </div>
              </>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
