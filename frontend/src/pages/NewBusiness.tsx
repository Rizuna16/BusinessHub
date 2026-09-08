import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { CreateBusinessInput, BusinessType } from '@/types/business';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

const BUSINESS_TYPE_OPTIONS: BusinessType[] = [
  'hotel', 'retail', 'umkm', 'restaurant', 'service',
  'production', 'garment', 'distributor', 'workshop', 'salon',
];

export const NewBusiness: React.FC = () => {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string | undefined>>({});
  const [serverError, setServerError] = useState('');

  const [form, setForm] = useState({
    name: '',
    description: '',
    business_type: 'umkm' as BusinessType,
    timezone: 'UTC',
    locale: 'en-US',
  });

  const handleChange = (field: keyof typeof form) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const value = e.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
    setServerError('');
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string | undefined> = {};
    if (!form.name.trim()) {
      newErrors.name = 'Business name is required.';
    } else if (form.name.trim().length < 2) {
      newErrors.name = 'Business name must be at least 2 characters.';
    }

    if (!form.timezone.trim()) {
      newErrors.timezone = 'Timezone is required.';
    } else if (form.timezone !== 'UTC' && !form.timezone.includes('/')) {
      newErrors.timezone = 'Must be a valid IANA timezone (e.g. Asia/Jakarta, UTC).';
    }

    if (!form.locale.trim()) {
      newErrors.locale = 'Locale is required.';
    } else if (!/^[a-z]{2}-[A-Z]{2}$/.test(form.locale) && !/^[a-z]{2}$/.test(form.locale)) {
      newErrors.locale = 'Must be in format like en-US or id-ID.';
    }

    setErrors(newErrors);
    return !Object.keys(newErrors).some((k) => newErrors[k] !== undefined);
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setIsSubmitting(true);
    setServerError('');
    try {
      const payload: CreateBusinessInput = {
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        business_type: form.business_type,
        timezone: form.timezone,
        locale: form.locale,
      };
      const business = await apiClient.createBusiness(payload);
      navigate(`/businesses/${business.id}`);
    } catch (err: any) {
      const msg = err?.message || 'Failed to create business.';
      if (msg.toLowerCase().includes('unauthorized') || err?.message?.includes('401')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Buat Bisnis Baru
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Buat bisnis baru untuk mulai mengelola operasional Anda.
          </p>
        </header>

        {serverError && (
          <div className="mb-6 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 p-4 text-rose-800 dark:text-rose-200">
            <span className="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {serverError}
            </span>
          </div>
        )}

        <Card
          title="Detail Bisnis"
          description="Isi informasi dasar bisnis Anda."
          footer={
            <div className="flex items-center justify-end gap-3">
              <Button variant="outline" onClick={() => navigate('/businesses')}>
                Batal
              </Button>
              <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={isSubmitting}>
                Buat Bisnis
              </Button>
            </div>
          }
        >
          <div className="space-y-6">
            <Input
              id="name"
              label="Nama Bisnis *"
              value={form.name}
              onChange={handleChange('name')}
              error={errors.name}
              placeholder="Contoh: Warung Makan Sari"
            />
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Deskripsi
              </label>
              <textarea
                id="description"
                rows={4}
                className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm transition-colors placeholder:text-slate-400 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-h-[80px] resize-y"
                placeholder="Deskripsi singkat tentang bisnis Anda (opsional)"
                value={form.description}
                onChange={handleChange('description')}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Tipe Bisnis *
              </label>
              <select
                id="business_type"
                className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm transition-colors text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-h-[40px]"
                value={form.business_type}
                onChange={(e) => handleChange('business_type')(e as React.ChangeEvent<HTMLSelectElement>)}
              >
                {BUSINESS_TYPE_OPTIONS.map((type) => (
                  <option key={type} value={type}>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-6 sm:grid-cols-2">
              <Input
                id="timezone"
                label="Timezone *"
                value={form.timezone}
                onChange={handleChange('timezone')}
                error={errors.timezone}
                placeholder="Asia/Jakarta"
              />
              <Input
                id="locale"
                label="Locale *"
                value={form.locale}
                onChange={handleChange('locale')}
                error={errors.locale}
                placeholder="en-US"
              />
            </div>
          </div>
        </Card>

        <div className="mt-6 text-center text-xs text-slate-500 dark:text-slate-400">
          Dengan membuat bisnis, Anda setuju menjadi pemilik (owner) bisnis ini.
        </div>
      </div>
    </div>
  );
};

export default NewBusiness;
