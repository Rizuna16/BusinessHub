import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../services/apiClient';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';

export const ForgotPassword: React.FC = () => {
  const [email, setEmail] = useState('');
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email) {
      setError('Email wajib diisi.');
      return;
    }

    try {
      setIsSubmitting(true);
      await apiClient.forgotPassword(email);
      setSuccess(true);
    } catch (err: any) {
      setError('Terjadi kesalahan. Silakan coba lagi.');
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
              Jika email terdaftar, instruksi reset telah dikirim ke email Anda.
            </div>
            <Link
              to="/login"
              className="block w-full text-center font-medium text-blue-600 hover:underline dark:text-blue-400"
            >
              Kembali ke Login
            </Link>
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
            Lupa password? Masukkan email Anda.
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

            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={isSubmitting}
              className="w-full"
            >
              {isSubmitting ? 'Mengirim...' : 'Kirim Link Reset'}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm">
            <Link
              to="/login"
              className="font-medium text-blue-600 hover:underline dark:text-blue-400"
            >
              Kembali ke Login
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default ForgotPassword;
