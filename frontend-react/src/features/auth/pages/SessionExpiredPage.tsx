import { useNavigate } from 'react-router-dom';
import { Button } from '../../../shared/components/ui/Button';
import { ShieldAlert, LogIn } from 'lucide-react';

export function SessionExpiredPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <div className="glass-panel max-w-md w-full p-8 rounded-2xl border border-slate-800 text-center space-y-5 shadow-2xl">
        <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto">
          <ShieldAlert className="w-6 h-6" />
        </div>

        <h2 className="text-xl font-bold text-slate-100">Session Expired</h2>

        <p className="text-xs text-slate-400 leading-relaxed">
          Your security token has expired or your session was invalidated. Please log in again to continue accessing your workspace.
        </p>

        <Button
          onClick={() => navigate('/login')}
          className="w-full"
          leftIcon={<LogIn className="w-4 h-4" />}
        >
          Return to Login
        </Button>
      </div>
    </div>
  );
}
