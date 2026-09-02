import React from 'react';

const NotFound: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900">
      <div className="text-center">
        <h1 className="text-5xl font-bold text-slate-900 dark:text-slate-100 mb-4">404</h1>
        <p className="text-2xl text-slate-500 dark:text-slate-400 mb-8">Halaman tidak ditemukan</p>
        <a href="/" className="inline-flex items-center justify-center font-medium rounded-lg px-5 py-2.5 bg-slate-200 hover:bg-slate-300 text-slate-800 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-100">
          Kembali ke Home
        </a>
      </div>
    </div>
  );
};

export default NotFound;