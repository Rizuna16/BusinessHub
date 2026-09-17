import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { DeliveryNote } from '@/types/deliveryNote';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export const DeliveryNoteDetail: React.FC = () => {
  const { businessId, deliveryNoteId } = useParams<{ businessId: string; deliveryNoteId: string }>();
  const navigate = useNavigate();

  const [deliveryNote, setDeliveryNote] = useState<DeliveryNote | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  const fetchDetail = useCallback(async () => {
    if (!businessId || !deliveryNoteId) return;
    try {
      setIsLoading(true);
      setError('');
      const res = await apiClient.getDeliveryNote(businessId, deliveryNoteId);
      setDeliveryNote(res);
    } catch (err: any) {
      setError(err?.message || 'Gagal memuat delivery note.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, deliveryNoteId]);

  const handleAction = useCallback(async (action: 'ready' | 'deliver' | 'cancel') => {
    if (!businessId || !deliveryNoteId) return;
    try {
      setError('');
      let res: DeliveryNote;
      if (action === 'ready') {
        res = await apiClient.readyDeliveryNote(businessId, deliveryNoteId);
      } else if (action === 'deliver') {
        res = await apiClient.deliverDeliveryNote(businessId, deliveryNoteId);
      } else {
        res = await apiClient.cancelDeliveryNote(businessId, deliveryNoteId);
      }
      setDeliveryNote(res);
    } catch (err: any) {
      setError(err?.message || 'Aksi gagal.');
    }
  }, [businessId, deliveryNoteId]);

  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  if (isLoading) {
    return <div className="p-6">Memuat detail...</div>;
  }

  if (error && !deliveryNote) {
    return <div className="p-6 text-rose-600">Error: {error}</div>;
  }

  if (!deliveryNote) {
    return <div className="p-6">Delivery Note tidak ditemukan.</div>;
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Delivery Note: {deliveryNote.delivery_number}</h1>
          <p className="text-sm text-slate-500">Sales Order ID: {deliveryNote.sales_order_id}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handlePrint}>
            Cetak / Print
          </Button>
          <Button variant="secondary" onClick={() => navigate(`/businesses/${businessId}/delivery-notes`)}>
            Kembali
          </Button>
          {deliveryNote.status === 'DRAFT' && (
            <Button variant="primary" onClick={() => handleAction('ready')}>
              READY
            </Button>
          )}
          {deliveryNote.status === 'READY' && (
            <Button variant="primary" onClick={() => handleAction('deliver')}>
              DELIVER
            </Button>
          )}
          {(deliveryNote.status === 'DRAFT' || deliveryNote.status === 'READY') && (
            <Button variant="danger" onClick={() => handleAction('cancel')}>
              CANCEL
            </Button>
          )}
        </div>
      </div>

      <Card className="p-6 space-y-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
        <div className="flex justify-between items-start border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <h2 className="text-2xl font-extrabold text-slate-900 dark:text-slate-100">SURAT JALAN</h2>
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400">No: {deliveryNote.delivery_number}</p>
          </div>
          <div className="text-right">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              deliveryNote.status === 'DRAFT' ? 'bg-amber-100 text-amber-800' :
              deliveryNote.status === 'READY' ? 'bg-blue-100 text-blue-800' :
              deliveryNote.status === 'DELIVERED' ? 'bg-emerald-100 text-emerald-800' :
              'bg-rose-100 text-rose-800'
            }`}>
              {deliveryNote.status}
            </span>
            <p className="text-xs text-slate-500 mt-1">Tanggal: {new Date(deliveryNote.delivery_date).toLocaleDateString()}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <h3 className="font-semibold text-slate-700 dark:text-slate-300">Tujuan Pengiriman:</h3>
            <p className="text-slate-600 dark:text-slate-400 whitespace-pre-line">{deliveryNote.shipping_address || '-'}</p>
            <p className="text-slate-600 dark:text-slate-400 mt-1">Penerima: {deliveryNote.recipient_name || '-'}</p>
            <p className="text-slate-600 dark:text-slate-400">Telepon: {deliveryNote.recipient_phone || '-'}</p>
          </div>
          <div className="text-right">
            <h3 className="font-semibold text-slate-700 dark:text-slate-300">Catatan:</h3>
            <p className="text-slate-600 dark:text-slate-400">{deliveryNote.notes || '-'}</p>
          </div>
        </div>

        <div>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-500">
                <th className="py-2">No</th>
                <th className="py-2">Produk</th>
                <th className="py-2">Variant</th>
                <th className="py-2 text-right">Dipesan</th>
                <th className="py-2 text-right">Terpenuhi</th>
                <th className="py-2 text-right">Dikirim</th>
                <th className="py-2">Satuan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-sm">
              {deliveryNote.lines.map((line, idx) => (
                <tr key={line.id}>
                  <td className="py-3">{idx + 1}</td>
                  <td className="py-3 font-medium text-slate-900 dark:text-slate-100">{line.product_name_snapshot}</td>
                  <td className="py-3 text-slate-500">{line.variant_snapshot || '-'}</td>
                  <td className="py-3 text-right">{line.ordered_quantity_snapshot}</td>
                  <td className="py-3 text-right">{line.fulfilled_quantity_snapshot}</td>
                  <td className="py-3 text-right font-bold text-slate-900 dark:text-slate-100">{line.delivery_quantity}</td>
                  <td className="py-3">{line.unit || 'pcs'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="grid grid-cols-2 gap-8 pt-12 border-t border-slate-200 dark:border-slate-800 text-center text-sm">
          <div>
            <p className="font-semibold text-slate-700 dark:text-slate-300">Hormat Kami,</p>
            <div className="h-20" />
            <p className="border-t border-slate-400 w-48 mx-auto pt-1 text-slate-500">( Pengirim / Gudang )</p>
          </div>
          <div>
            <p className="font-semibold text-slate-700 dark:text-slate-300">Penerima,</p>
            <div className="h-20" />
            <p className="border-t border-slate-400 w-48 mx-auto pt-1 text-slate-500">( Nama & Tanda Tangan )</p>
          </div>
        </div>
      </Card>
    </div>
  );
};
