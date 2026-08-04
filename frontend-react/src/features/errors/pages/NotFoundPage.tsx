import { useNavigate } from 'react-router-dom';
import { Button } from '../../../shared/components/ui/Button';
import { HelpCircle, Home } from 'lucide-react';

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-4">
      <div className="p-4 bg-slate-900 border border-slate-800 rounded-full mb-4">
        <HelpCircle className="w-12 h-12 text-blue-400" />
      </div>
      <h1 className="text-4xl font-extrabold text-slate-100 tracking-tight">404</h1>
      <h2 className="text-lg font-bold text-slate-200 mt-2">Page Not Found</h2>
      <p className="text-xs text-slate-400 mt-1 max-w-sm">
        The page or resource you are looking for does not exist or has been moved.
      </p>
      <Button className="mt-6" onClick={() => navigate('/')} leftIcon={<Home className="w-4 h-4" />}>
        Back to Dashboard
      </Button>
    </div>
  );
}
