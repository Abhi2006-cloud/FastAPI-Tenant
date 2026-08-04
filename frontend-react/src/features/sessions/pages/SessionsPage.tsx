import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { storage } from '../../../shared/utils/storage';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../shared/components/ui/Card';
import { Button } from '../../../shared/components/ui/Button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../../shared/components/ui/Table';
import { Badge } from '../../../shared/components/ui/Badge';
import { useToast } from '../../../shared/components/ui/Toast';
import { TableSkeleton } from '../../../shared/components/ui/Skeleton';
import { ShieldCheck, Laptop, Smartphone, Globe, LogOut, CheckCircle2 } from 'lucide-react';
import { SessionItem } from '../../auth/types';

export function SessionsPage() {
  const { toast } = useToast();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const currentSessionId = storage.getSessionId();

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    try {
      const param = currentSessionId ? `?current_session_id=${currentSessionId}` : '';
      const res = await apiClient.get(`/auth/sessions${param}`);
      setSessions(res.data.sessions || []);
    } catch {
      toast('error', 'Failed to load device sessions');
    } finally {
      setIsLoading(false);
    }
  }, [currentSessionId, toast]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleRevokeSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to revoke this session remotely?')) return;
    try {
      await apiClient.delete(`/auth/sessions/${sessionId}`);
      toast('success', 'Session revoked successfully');
      await fetchSessions();
    } catch {
      toast('error', 'Failed to revoke session');
    }
  };

  const handleLogoutAllOther = async () => {
    if (!confirm('Sign out all other devices keeping current device active?')) return;
    try {
      const refreshToken = storage.getRefreshToken();
      await apiClient.post('/auth/logout-all', {
        refresh_token: refreshToken,
        keep_current: true,
      });
      toast('success', 'All other active sessions revoked');
      await fetchSessions();
    } catch {
      toast('error', 'Failed to logout other devices');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-purple-400" />
            Device Security & Active Sessions
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Monitor and manage active security tokens and device sessions logged into your account
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleLogoutAllOther}
          leftIcon={<LogOut className="w-4 h-4 text-rose-400" />}
        >
          Revoke All Other Devices
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active Devices ({sessions.length})</CardTitle>
          <CardDescription>Real-time device tracking with IP address and User-Agent parsing</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={3} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device & Browser</TableHead>
                  <TableHead>IP Address</TableHead>
                  <TableHead>Last Active</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.map((s) => {
                  const isCurrent = s.is_current || s.id === currentSessionId;
                  const isMobile = s.platform?.toLowerCase().includes('mobile');

                  return (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium text-slate-200">
                        <div className="flex items-center gap-2.5">
                          <div className="p-2 rounded-lg bg-slate-800 text-purple-400">
                            {isMobile ? <Smartphone className="w-4 h-4" /> : <Laptop className="w-4 h-4" />}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span>{s.device_name || s.browser || 'Unknown Browser'}</span>
                              {isCurrent && (
                                <Badge variant="success" size="sm">
                                  This Device
                                </Badge>
                              )}
                            </div>
                            <span className="text-[10px] text-slate-400 block font-mono">{s.platform || 'Desktop'}</span>
                          </div>
                        </div>
                      </TableCell>

                      <TableCell className="text-xs font-mono text-slate-300">
                        <div className="flex items-center gap-1">
                          <Globe className="w-3.5 h-3.5 text-slate-400" />
                          <span>{s.ip_address || '127.0.0.1'}</span>
                        </div>
                      </TableCell>

                      <TableCell className="text-xs text-slate-400">
                        {new Date(s.last_used_at || s.created_at).toLocaleString()}
                      </TableCell>

                      <TableCell>
                        <Badge variant="purple" size="sm" className="gap-1">
                          <CheckCircle2 className="w-3 h-3 text-purple-400" /> Active
                        </Badge>
                      </TableCell>

                      <TableCell className="text-right">
                        {!isCurrent && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRevokeSession(s.id)}
                            className="text-rose-400 hover:text-rose-300"
                          >
                            Revoke
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
