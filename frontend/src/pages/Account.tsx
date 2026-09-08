import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { apiClient } from '@/services/apiClient';
import type { Account, AccountUpdatePayload } from '@/types/account';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';

type FormErrors = Partial<Record<keyof AccountUpdatePayload, string>>;

const AVATAR_FALLBACK_CLASS = 'bg-indigo-500 dark:bg-indigo-600 text-white';

const AccountAvatar: React.FC<{ account: Account | null; isEditing: boolean }> = ({ account, isEditing }) => {
  const displayName = account?.display_name || account?.user_id?.slice(0, 2) || 'US';
  const initials = displayName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const sizeClass = isEditing ? 'w-20 h-20 text-xl' : 'w-12 h-12 text-sm';

  if (account?.avatar_url) {
    return (
      <img
        src={account.avatar_url}
        alt={displayName || 'Avatar'}
        className={`${sizeClass} rounded-full object-cover border-2 border-slate-200 dark:border-slate-700`}
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = 'none';
          (e.target as HTMLImageElement).parentElement!.classList.add(AVATAR_FALLBACK_CLASS);
          (e.target as HTMLImageElement).parentElement!.classList.remove('bg-transparent');
          const initialSpan = (e.target as HTMLImageElement).parentElement!.querySelector('span');
          if (initialSpan) {
            initialSpan.classList.remove('hidden');
            initialSpan.classList.add(AVATAR_FALLBACK_CLASS);
          }
        }}
      />
    );
  }

  return (
    <div
      className={`${sizeClass} rounded-full flex items-center justify-center font-bold ${AVATAR_FALLBACK_CLASS} border-2 border-slate-200 dark:border-slate-700 overflow-hidden`}
    >
      <span className="hidden">{initials}</span>
      <span className={initials === '' ? 'text-xs' : ''}>{initials || 'US'}</span>
    </div>
  );
};

export const AccountPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [account, setAccount] = useState<Account | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string>('');
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  const fetchAccount = useCallback(async () => {
    try {
      setIsLoading(true);
      setServerError('');
      const data = await apiClient.getAccount();
      setAccount(data);
    } catch (err: any) {
      const msg = err?.message || 'Failed to load account.';
      if (err?.message?.includes('401') || msg.toLowerCase().includes('unauthorized')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [navigate]);

  React.useEffect(() => {
    fetchAccount();
  }, [fetchAccount]);

  const handleEdit = () => {
    setIsEditing(true);
    setSaveSuccess(false);
    setErrors({});
  };

  const handleCancel = () => {
    setIsEditing(false);
    setErrors({});
    setSaveSuccess(false);
  };

  const [form, setForm] = useState<AccountUpdatePayload>({
    display_name: '',
    phone: '',
    avatar_url: '',
    timezone: 'UTC',
    locale: 'en-US',
  });

  const localField = (key: keyof AccountUpdatePayload): string => {
    const val = form[key];
    return val === null || val === undefined ? '' : String(val);
  };

  React.useEffect(() => {
    if (account) {
      setForm({
        display_name: account.display_name ?? '',
        phone: account.phone ?? '',
        avatar_url: account.avatar_url ?? '',
        timezone: account.timezone ?? 'UTC',
        locale: account.locale ?? 'en-US',
      });
    }
  }, [account]);

  const handleInputChange = (field: keyof AccountUpdatePayload) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const value = e.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
    setServerError('');
    setSaveSuccess(false);
  };

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    const displayName = form.display_name?.trim() ?? '';
    if (!displayName) {
      newErrors.display_name = 'Display name is required.';
    } else if (displayName.length < 2) {
      newErrors.display_name = 'Display name must be at least 2 characters.';
    }

    const phone = form.phone?.trim() ?? '';
    if (phone) {
      const phonePattern = /^[\+]?[\d\s\-\(\)]{7,20}$/;
      if (!phonePattern.test(phone)) {
        newErrors.phone = 'Invalid phone number format.';
      }
    }

    const avatarUrl = form.avatar_url?.trim() ?? '';
    if (avatarUrl) {
      const isValidUrl = avatarUrl.startsWith('http://') || avatarUrl.startsWith('https://');
      if (!isValidUrl) {
        newErrors.avatar_url = 'Avatar URL must be a valid HTTP or HTTPS URL.';
      } else {
        try {
          new URL(avatarUrl);
        } catch {
          newErrors.avatar_url = 'Avatar URL is not a valid URL.';
        }
      }
    }

    const tz = form.timezone?.trim() ?? '';
    if (tz && tz !== 'UTC' && !tz.includes('/')) {
      newErrors.timezone = 'Timezone must be a valid IANA identifier (e.g. Asia/Jakarta, UTC).';
    }

    const loc = form.locale?.trim() ?? '';
    if (loc) {
      const localePattern = /^[a-z]{2}-[A-Z]{2}$/;
      if (!localePattern.test(loc) && !/^[a-z]{2}$/.test(loc)) {
        newErrors.locale = 'Locale must be in format like en-US or id-ID.';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) {
      return;
    }
    setIsSaving(true);
    setServerError('');
    setSaveSuccess(false);

    const payload: AccountUpdatePayload = {
      display_name: form.display_name?.trim() || '',
      phone: form.phone?.trim() || null,
      avatar_url: form.avatar_url?.trim() || null,
      timezone: form.timezone?.trim() || 'UTC',
      locale: form.locale?.trim() || 'en-US',
    };

    try {
      const updated = await apiClient.updateAccount(payload);
      setAccount(updated);
      setIsEditing(false);
      setSaveSuccess(true);
    } catch (err: any) {
      const msg = err?.message || 'Failed to save changes.';
      if (msg.toLowerCase().includes('unauthorized') || err?.message?.includes('401')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900">
        <Loading size="lg" text="Loading account..." />
      </div>
    );
  }

  if (serverError && !account) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900">
        <ErrorState message={serverError} onRetry={fetchAccount} />
      </div>
    );
  }

  if (!account) {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 flex flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-4">
            <AccountAvatar account={account} isEditing={false} />
            <div className="text-center sm:text-left">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                Akun Saya
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Kelola profil dan preferensi akun Anda.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <Button variant="outline" size="sm" onClick={handleCancel} disabled={isSaving}>
                  Batal
                </Button>
                <Button size="sm" onClick={handleSave} isLoading={isSaving} disabled={isSaving}>
                  Simpan
                </Button>
              </>
            ) : (
              <Button size="sm" onClick={handleEdit} disabled={isSaving}>
                Edit
              </Button>
            )}
          </div>
        </header>

        {saveSuccess && (
          <div className="mb-6 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/50 p-4 text-emerald-800 dark:text-emerald-200">
            <span className="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Perubahan berhasil disimpan.
            </span>
          </div>
        )}

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

        <Card className="mb-6">
          <div className="space-y-6">
            <div className="flex flex-col items-center gap-4 sm:flex-row">
              <div className="flex-shrink-0">
                <AccountAvatar account={account} isEditing={isEditing} />
              </div>
              <div className="flex-1">
                <p className="text-xs text-slate-500 dark:text-slate-400">Avatar URL (optional)</p>
                {isEditing ? (
                  <Input
                    id="avatar_url"
                    label="Avatar URL"
                    value={localField('avatar_url')}
                    onChange={handleInputChange('avatar_url')}
                    error={errors.avatar_url}
                    placeholder="https://example.com/avatar.png"
                  />
                ) : (
                  <div className="mt-1 break-all text-sm text-slate-600 dark:text-slate-300">
                    {account.avatar_url || 'Belum diatur'}
                  </div>
                )}
              </div>
            </div>

            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Email
                </label>
                <Input
                  id="email"
                  value={user?.email ?? ''}
                  readOnly
                  disabled
                  className="bg-slate-100 dark:bg-slate-800 cursor-not-allowed"
                />
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Email tidak dapat diubah dari akun ini.
                </p>
              </div>

              <div>
                {isEditing ? (
                  <>
                    <Input
                      id="display_name"
                      label="Display Name"
                      value={localField('display_name')}
                      onChange={handleInputChange('display_name')}
                      error={errors.display_name}
                      placeholder="Nama tampilan"
                    />
                  </>
                ) : (
                  <>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Display Name
                    </label>
                    <div className="mt-1 text-sm text-slate-900 dark:text-slate-100">
                      {account.display_name || '-'}
                    </div>
                  </>
                )}
              </div>

              <div>
                {isEditing ? (
                  <Input
                    id="phone"
                    label="Phone"
                    value={localField('phone')}
                    onChange={handleInputChange('phone')}
                    error={errors.phone}
                    placeholder="+6281234567890"
                  />
                ) : (
                  <>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Phone
                    </label>
                    <div className="mt-1 text-sm text-slate-900 dark:text-slate-100">
                      {account.phone || 'Belum diatur'}
                    </div>
                  </>
                )}
              </div>

              <div>
                {isEditing ? (
                  <Input
                    id="timezone"
                    label="Timezone"
                    value={localField('timezone')}
                    onChange={handleInputChange('timezone')}
                    error={errors.timezone}
                    placeholder="Asia/Jakarta"
                  />
                ) : (
                  <>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Timezone
                    </label>
                    <div className="mt-1 text-sm text-slate-900 dark:text-slate-100">
                      {account.timezone || '-'}
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                {isEditing ? (
                  <Input
                    id="locale"
                    label="Locale"
                    value={localField('locale')}
                    onChange={handleInputChange('locale')}
                    error={errors.locale}
                    placeholder="en-US"
                  />
                ) : (
                  <>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Locale
                    </label>
                    <div className="mt-1 text-sm text-slate-900 dark:text-slate-100">
                      {account.locale || '-'}
                    </div>
                  </>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Account ID
                </label>
                <div className="mt-1 break-all text-sm text-slate-500 dark:text-slate-400">
                  {account.id}
                </div>
              </div>
            </div>
          </div>
        </Card>

        <Card className="mb-6">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Keamanan
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Email dan kata sandi dikelola di halaman Authentication. Fitur ganti email/password
              akan tersedia pada fitur keamanan akun di lain waktu.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/app')}
              className="w-full sm:w-auto"
            >
              Kembali ke Dashboard
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default AccountPage;
