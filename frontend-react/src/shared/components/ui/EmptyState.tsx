import React from 'react';
import { FolderOpen } from 'lucide-react';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({
  icon = <FolderOpen className="w-10 h-10 text-slate-500" />,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/30">
      <div className="p-3 bg-slate-800/40 rounded-full mb-3">{icon}</div>
      <h4 className="text-base font-semibold text-slate-200">{title}</h4>
      {description && <p className="text-xs text-slate-400 mt-1 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
