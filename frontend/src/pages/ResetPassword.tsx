import React, { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../services/apiClient';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';

export const ResetPassword: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12 dark:bg-slate-950 sm:px-6 lg:px-8">
        <div className="w-full max-w-md space-y-8">
          <Card>
            <div className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-400">
              Token reset tidak ditemukan. Silakan minta reset password baru.
            </div>
            <Link
              to="/forgot-password"
              className="block w-full text-center font-medium text-blue-600 hover:underline dark:text-blue-400"
            >
              Minta Reset Baru
            </Link>
          </Card>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!newPassword || !confirmPassword) {
      setError('Semua field wajib diisi.');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password harus minimal 8 karakter.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Konfirmasi password tidak cocok.');
      return;
    }

    try {
      setIsSubmitting(true);
      await apiClient.resetPassword(token, newPassword, confirmPassword);
      setSuccess(true);
    } catch (err: any) {
      const msg = err.message || '';
      if (msg.includes('tidak valid') || msg.includes('kedaluwarsa')) {
        setError('Token tidak valid atau sudah kedaluwarsa. Silakan minta reset baru.');
      } else if (msg.includes('tidak cocok')) {
        setError('Konfirmasi password tidak cocok.');
      } else {
        setError(msg || 'Terjadi kesalahan. Silakan coba lagi.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12 dark:bg-slate-950 sm:px-6 lg:px-8">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              BusinessHub
            </h1>
          </div>
          <Card>
            <div className="mb-4 rounded-md bg-green-50 p-4 text-sm text-green-700 dark:bg-green-950/50 dark:text-green-400">
              Password berhasil diubah. Silakan login.
            </div>
            <Button
              variant="primary"
              size="lg"
              className="w-full"
              onClick={() => navigate('/login')}
            >
              Login
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12 dark:bg-slate-950 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            BusinessHub
          </h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Buat password baru
          </p>
        </div>

        <Card>
          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <Input
                label="Password Baru"
                type={showPassword ? 'text' : 'password'}
                placeholder="min. 8 karakter"
                value={newPassword}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="absolute right-3 top-9 text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? 'Sembunyikan' : 'Tampilkan'}
              </button>
            </div>

            <Input
              label="Konfirmasi Password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Ulangi password"
              value={confirmPassword}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfirmPassword(e.target.value)}
              required
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={isSubmitting}
              className="w-full"
            >
              {isSubmitting ? 'Menyimpan...' : 'Reset Password'}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
};

export default ResetPassword;
