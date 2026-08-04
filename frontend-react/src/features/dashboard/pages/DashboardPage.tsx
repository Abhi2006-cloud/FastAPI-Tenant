import { useState, useEffect } from 'react';
import { useOrg } from '../../organizations/context/OrgContext';
import { useAuth } from '../../auth/context/AuthContext';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../shared/components/ui/Card';
import { Badge } from '../../../shared/components/ui/Badge';
import { Button } from '../../../shared/components/ui/Button';
import { apiClient } from '../../../shared/api/client';
import {
  Building2,
  FolderKanban,
  Mail,
  ShieldCheck,
  Activity,
  ArrowRight,
  RefreshCw,
  Database,
  Search,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function DashboardPage() {
  const { activeOrg, userRoleInActiveOrg } = useOrg();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [fileStats, setFileStats] = useState<{ total_files: number; total_bytes: number } | null>(null);
  const [emailStats, setEmailStats] = useState<{ total_sent: number; total_failed: number } | null>(null);
  const [sessionCount, setSessionCount] = useState<number>(0);
  const [healthInfo, setHealthInfo] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      if (activeOrg) {
        const fileRes = await apiClient.get(`/files/stats`);
        setFileStats(fileRes.data);
      }

      const [emailRes, sessionRes, healthRes] = await Promise.allSettled([
        apiClient.get('/email/stats'),
        apiClient.get('/auth/sessions'),
        apiClient.get('/health'),
      ]);

      if (emailRes.status === 'fulfilled') setEmailStats(emailRes.value.data);
      if (sessionRes.status === 'fulfilled') setSessionCount(sessionRes.value.data?.total || 0);
      if (healthRes.status === 'fulfilled') setHealthInfo(healthRes.value.data);
    } catch {
      // Fallbacks handle missing stats gracefully
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [activeOrg]);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-blue-950/40 via-slate-900 to-indigo-950/40 p-6 rounded-2xl border border-blue-500/20">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Welcome back, <span className="text-blue-400">{user?.email?.split('@')[0]}</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Active Workspace: <strong className="text-slate-200">{activeOrg ? activeOrg.name : 'None Selected'}</strong>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={loadDashboardData}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
          <Button size="sm" onClick={() => navigate('/files')} rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
            Manage Files
          </Button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Org Card */}
        <Card className="hover:border-blue-500/30 transition-all">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Current Organization</CardTitle>
            <Building2 className="w-4 h-4 text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-slate-100 truncate">{activeOrg ? activeOrg.name : 'No Org'}</div>
            <div className="flex items-center gap-2 mt-2">
              <Badge variant="purple" size="sm">
                Role: {userRoleInActiveOrg || 'member'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Files Stats Card */}
        <Card className="hover:border-blue-500/30 transition-all">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Storage & Files</CardTitle>
            <FolderKanban className="w-4 h-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-slate-100">
              {fileStats ? `${fileStats.total_files} Files` : '0 Files'}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Used: {fileStats ? formatBytes(fileStats.total_bytes) : '0 B'}
            </p>
          </CardContent>
        </Card>

        {/* Email Stats Card */}
        <Card className="hover:border-blue-500/30 transition-all">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Email Delivery</CardTitle>
            <Mail className="w-4 h-4 text-sky-400" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-slate-100">
              {emailStats ? `${emailStats.total_sent} Sent` : '0 Sent'}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Failed: <span className="text-rose-400 font-semibold">{emailStats?.total_failed || 0}</span>
            </p>
          </CardContent>
        </Card>

        {/* Sessions Security Card */}
        <Card className="hover:border-blue-500/30 transition-all">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Active Sessions</CardTitle>
            <ShieldCheck className="w-4 h-4 text-purple-400" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-slate-100">{sessionCount} Devices</div>
            <p className="text-xs text-emerald-400 mt-1 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Protected
            </p>
          </CardContent>
        </Card>
      </div>

      {/* System Infrastructure Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" />
            Backend Infrastructure Health
          </CardTitle>
          <CardDescription>Live health checks across micro-services</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-center">
              <Database className="w-4 h-4 text-emerald-400 mx-auto mb-1" />
              <span className="text-xs text-slate-400 block">Database</span>
              <Badge variant={healthInfo?.database === 'connected' ? 'success' : 'danger'} size="sm" className="mt-1">
                {String(healthInfo?.database || 'checking')}
              </Badge>
            </div>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-center">
              <Activity className="w-4 h-4 text-rose-400 mx-auto mb-1" />
              <span className="text-xs text-slate-400 block">Redis Cache</span>
              <Badge variant={healthInfo?.redis === 'connected' ? 'success' : 'warning'} size="sm" className="mt-1">
                {String(healthInfo?.redis || 'checking')}
              </Badge>
            </div>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-center">
              <Search className="w-4 h-4 text-sky-400 mx-auto mb-1" />
              <span className="text-xs text-slate-400 block">Meilisearch</span>
              <Badge variant={healthInfo?.search === 'connected' || healthInfo?.search === 'ok' ? 'success' : 'warning'} size="sm" className="mt-1">
                {String(healthInfo?.search || 'fallback')}
              </Badge>
            </div>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-center">
              <Mail className="w-4 h-4 text-amber-400 mx-auto mb-1" />
              <span className="text-xs text-slate-400 block">Email Engine</span>
              <Badge variant="info" size="sm" className="mt-1">
                {String(healthInfo?.email || 'ready')}
              </Badge>
            </div>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-center">
              <Activity className="w-4 h-4 text-purple-400 mx-auto mb-1" />
              <span className="text-xs text-slate-400 block">Worker Jobs</span>
              <Badge variant="purple" size="sm" className="mt-1">
                {String(healthInfo?.worker || 'idle')}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
