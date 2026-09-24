import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../services/apiClient';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';

function mapLoginError(err: any): string {
  const msg = String(err?.message || '');

  if (msg.includes('Invalid email or password') || msg.includes('401')) {
    return 'Email atau password salah.';
  }
  if (msg.includes('inactive') || msg.includes('403')) {
    return 'Akun tidak aktif. Hubungi administrator.';
  }
  if (msg.includes('network') || msg.includes('fetch') || msg.includes('Failed to fetch')) {
    return 'Tidak dapat terhubung ke server. Periksa koneksi dan coba lagi.';
  }
  if (msg.includes('500') || msg.includes('502') || msg.includes('503')) {
    return 'Terjadi kesalahan pada server. Silakan coba lagi.';
  }

  return msg || 'Terjadi kesalahan. Silakan coba lagi.';
}

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError('Semua field wajib diisi.');
      return;
    }

    try {
      setIsSubmitting(true);
      await login({ email, password });
      const userData = await apiClient.getMe();
      if (userData.platform_role === 'SUPER_ADMIN') {
        navigate('/platform/dashboard');
      } else {
        navigate('/app');
      }
    } catch (err: any) {
      setError(mapLoginError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12 dark:bg-slate-950 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            BusinessHub
          </h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Masuk ke akun Anda
          </p>
        </div>

        <Card>
          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <Input
              label="Email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
              required
            />

            <div className="relative">
              <Input
                label="Password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
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

            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={isSubmitting}
              className="w-full"
            >
              {isSubmitting ? 'Masuk...' : 'Masuk'}
            </Button>
          </form>

          <div className="mt-4 text-center text-sm">
            <Link
              to="/forgot-password"
              className="font-medium text-blue-600 hover:underline dark:text-blue-400"
            >
              Lupa password?
            </Link>
          </div>

          <div className="mt-6 text-center text-sm">
            <span className="text-slate-600 dark:text-slate-400">
              Belum punya akun?{' '}
            </span>
            <Link
              to="/register"
              className="font-medium text-blue-600 hover:underline dark:text-blue-400"
            >
              Daftar di sini
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Login;
