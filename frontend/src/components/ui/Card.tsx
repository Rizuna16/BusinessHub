import React from 'react';

export interface CardProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({
  title,
  description,
  children,
  footer,
  className = '',
}) => {
  return (
    <div className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xs overflow-hidden ${className}`}>
      {(title || description) && (
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700/60">
          {title && <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h3>}
          {description && <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{description}</p>}
        </div>
      )}
      <div className="p-5">{children}</div>
      {footer && (
        <div className="px-5 py-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-end gap-3">
          {footer}
        </div>
      )}
    </div>
  );
};
