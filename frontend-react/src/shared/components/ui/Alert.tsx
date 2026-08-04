import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'info' | 'success' | 'warning' | 'danger';
  title?: string;
}

export function Alert({ variant = 'info', title, children, className, ...props }: AlertProps) {
  const icons = {
    info: <Info className="w-5 h-5 text-sky-400 shrink-0" />,
    success: <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />,
    danger: <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />,
  };

  const variants = {
    info: 'bg-sky-500/10 border-sky-500/20 text-sky-200',
    success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-200',
    warning: 'bg-amber-500/10 border-amber-500/20 text-amber-200',
    danger: 'bg-rose-500/10 border-rose-500/20 text-rose-200',
  };

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-xl border text-xs leading-relaxed',
        variants[variant],
        className
      )}
      {...props}
    >
      {icons[variant]}
      <div className="space-y-0.5">
        {title && <h5 className="font-semibold text-sm">{title}</h5>}
        <div>{children}</div>
      </div>
    </div>
  );
}
