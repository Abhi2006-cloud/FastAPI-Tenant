import { useAuth } from '../../auth/context/AuthContext';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../shared/components/ui/Card';
import { Badge } from '../../../shared/components/ui/Badge';
import { Button } from '../../../shared/components/ui/Button';
import { UserCheck, ShieldCheck, Mail, Calendar, KeyRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function ProfilePage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <UserCheck className="w-6 h-6 text-blue-400" />
          User Profile & Security
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Account identity and credentials security overview
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 font-bold text-2xl text-white flex items-center justify-center shadow-lg shadow-blue-500/20">
              {user?.email?.[0]?.toUpperCase()}
            </div>
            <div>
              <CardTitle className="text-xl">{user?.email}</CardTitle>
              <CardDescription className="font-mono text-[10px] mt-0.5">User ID: {user?.id}</CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-t border-b border-slate-800 py-4 text-xs">
            <div className="flex items-center gap-3">
              <Mail className="w-4 h-4 text-slate-400" />
              <div>
                <span className="text-slate-400 block font-semibold">Primary Email</span>
                <span className="text-slate-100">{user?.email}</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Calendar className="w-4 h-4 text-slate-400" />
              <div>
                <span className="text-slate-400 block font-semibold">Account Created</span>
                <span className="text-slate-100">
                  {user?.created_at ? new Date(user.created_at).toLocaleString() : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div>
              <h4 className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Active Device Sessions
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5">Manage logged in browsers and remote logout</p>
            </div>
            <Button variant="secondary" size="sm" onClick={() => navigate('/sessions')} leftIcon={<KeyRound className="w-3.5 h-3.5" />}>
              Manage Sessions
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
