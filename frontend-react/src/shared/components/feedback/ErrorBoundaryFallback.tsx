import { useRouteError, useNavigate } from 'react-router-dom';
import { Button } from '../ui/Button';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';

export function ErrorBoundaryFallback() {
  const error = useRouteError() as { message?: string; statusText?: string };
  const navigate = useNavigate();

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center">
      <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-full mb-4">
        <AlertCircle className="w-10 h-10 text-rose-400" />
      </div>
      <h2 className="text-xl font-bold text-slate-100">Something went wrong</h2>
      <p className="text-xs text-slate-400 mt-1 max-w-md">
        {error?.message || error?.statusText || 'An unexpected application error occurred while rendering this page.'}
      </p>

      <div className="flex gap-3 mt-6">
        <Button variant="secondary" size="sm" onClick={() => window.location.reload()} leftIcon={<RefreshCw className="w-3.5 h-3.5" />}>
          Reload Page
        </Button>
        <Button size="sm" onClick={() => navigate('/')} leftIcon={<Home className="w-3.5 h-3.5" />}>
          Go to Dashboard
        </Button>
      </div>
    </div>
  );
}
