import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../shared/components/ui/Card';
import { Button } from '../../../shared/components/ui/Button';
import { Input } from '../../../shared/components/ui/Input';
import { Badge } from '../../../shared/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../../shared/components/ui/Table';
import { Modal } from '../../../shared/components/ui/Modal';
import { useToast } from '../../../shared/components/ui/Toast';
import { TableSkeleton } from '../../../shared/components/ui/Skeleton';
import { Mail, Send, RefreshCw, AlertCircle, CheckCircle2, Eye, Server } from 'lucide-react';

interface EmailLog {
  id: string;
  recipient: string;
  subject: string;
  status: string;
  provider: string;
  body?: string;
  created_at: string;
}

interface EmailStats {
  total_sent: number;
  total_failed: number;
}

export function EmailPage() {
  const { toast } = useToast();

  const [stats, setStats] = useState<EmailStats | null>(null);
  const [logs, setLogs] = useState<EmailLog[]>([]);
  const [healthDetail, setHealthDetail] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Test Email State
  const [testRecipient, setTestRecipient] = useState('');
  const [testSubject, setTestSubject] = useState('Test Email from React App');
  const [testBody, setTestBody] = useState('Hello! This is a test email sent from the new React frontend.');
  const [isSending, setIsSending] = useState(false);

  // Detail Modal State
  const [selectedLog, setSelectedLog] = useState<EmailLog | null>(null);

  const fetchEmailData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [statsRes, logsRes, healthRes] = await Promise.all([
        apiClient.get<EmailStats>('/email/stats'),
        apiClient.get('/email/logs'),
        apiClient.get('/health'),
      ]);

      setStats(statsRes.data);
      const rawLogs = logsRes.data?.logs || logsRes.data?.items || logsRes.data;
      setLogs(Array.isArray(rawLogs) ? rawLogs : []);
      setHealthDetail(healthRes.data?.email_detail || null);
    } catch {
      toast('error', 'Failed to load email infrastructure data');
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchEmailData();
  }, [fetchEmailData]);

  const handleSendTestEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testRecipient.trim()) return;
    setIsSending(true);
    try {
      await apiClient.post('/email/test', {
        to_email: testRecipient,
        subject: testSubject,
        template_name: 'test_email',
        context: { message: testBody },
      });
      toast('success', 'Test email dispatched successfully');
      setTestRecipient('');
      await fetchEmailData();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to send test email';
      toast('error', msg);
    } finally {
      setIsSending(false);
    }
  };

  const handleRetryEmail = async (logId: string) => {
    try {
      await apiClient.post(`/email/logs/${logId}/retry`);
      toast('success', 'Email retry job queued');
      await fetchEmailData();
    } catch {
      toast('error', 'Failed to retry email delivery');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Mail className="w-6 h-6 text-sky-400" />
          Email Infrastructure
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Monitor email providers, delivery logs, test email runner, and retry failed jobs
        </p>
      </div>

      {/* Provider Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-slate-400 flex items-center justify-between">
              Provider Health
              <Server className="w-4 h-4 text-sky-400" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-slate-100 capitalize">
              {String(healthDetail?.status || 'connected')}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Active Mode: <strong className="text-sky-300 font-mono">{String(healthDetail?.mode || 'console')}</strong>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-slate-400">Total Delivered</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-emerald-400">{stats?.total_sent || 0}</div>
            <p className="text-[11px] text-slate-400 mt-1">Successful deliveries</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-slate-400">Delivery Failures</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-rose-400">{stats?.total_failed || 0}</div>
            <p className="text-[11px] text-slate-400 mt-1">Failed delivery jobs</p>
          </CardContent>
        </Card>
      </div>

      {/* Test Email Form */}
      <Card>
        <CardHeader>
          <CardTitle>Send Test Email</CardTitle>
          <CardDescription>Dispatch a test email through configured providers</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSendTestEmail} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Recipient Email"
                type="email"
                placeholder="test@example.com"
                value={testRecipient}
                onChange={(e) => setTestRecipient(e.target.value)}
                required
              />
              <Input
                label="Subject"
                value={testSubject}
                onChange={(e) => setTestSubject(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">Message Body</label>
              <textarea
                rows={3}
                value={testBody}
                onChange={(e) => setTestBody(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end">
              <Button type="submit" isLoading={isSending} leftIcon={<Send className="w-3.5 h-3.5" />}>
                Send Test Email
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Email Delivery Logs Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Email Delivery Logs</CardTitle>
            <CardDescription>Audit history of queued and delivered emails</CardDescription>
          </div>
          <Button variant="secondary" size="sm" onClick={fetchEmailData} leftIcon={<RefreshCw className="w-3.5 h-3.5" />}>
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={4} />
          ) : logs.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400">No email logs found.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Recipient</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Sent At</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-medium text-slate-200">{log.recipient}</TableCell>
                    <TableCell className="text-slate-300 truncate max-w-[200px]">{log.subject}</TableCell>
                    <TableCell>
                      {log.status === 'sent' && (
                        <Badge variant="success" size="sm" className="gap-1">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Sent
                        </Badge>
                      )}
                      {log.status === 'failed' && (
                        <Badge variant="danger" size="sm" className="gap-1">
                          <AlertCircle className="w-3 h-3 text-rose-400" /> Failed
                        </Badge>
                      )}
                      {log.status !== 'sent' && log.status !== 'failed' && (
                        <Badge variant="warning" size="sm">
                          {log.status}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {new Date(log.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="sm" onClick={() => setSelectedLog(log)}>
                          <Eye className="w-3.5 h-3.5 text-slate-400" />
                        </Button>
                        {log.status === 'failed' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRetryEmail(log.id)}
                            className="text-amber-400 hover:text-amber-300"
                          >
                            Retry
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Log Detail Modal */}
      <Modal
        isOpen={Boolean(selectedLog)}
        onClose={() => setSelectedLog(null)}
        title="Email Log Payload Details"
      >
        {selectedLog && (
          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <div>
                <span className="text-slate-400 font-semibold block">Recipient:</span>
                <span className="text-slate-100">{selectedLog.recipient}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Subject:</span>
                <span className="text-slate-100">{selectedLog.subject}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Status:</span>
                <span className="text-slate-200 font-mono">{selectedLog.status}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Body:</span>
                <p className="text-slate-300 whitespace-pre-wrap bg-slate-900 p-2 rounded border border-slate-800 mt-1">
                  {selectedLog.body || 'No preview body stored.'}
                </p>
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <Button size="sm" onClick={() => setSelectedLog(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
