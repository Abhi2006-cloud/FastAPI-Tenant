import { useState, useEffect, useCallback } from 'react';
import { useOrg } from '../../organizations/context/OrgContext';
import { apiClient } from '../../../shared/api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../shared/components/ui/Card';
import { Input } from '../../../shared/components/ui/Input';
import { Button } from '../../../shared/components/ui/Button';
import { Badge } from '../../../shared/components/ui/Badge';
import { TableSkeleton } from '../../../shared/components/ui/Skeleton';
import { useToast } from '../../../shared/components/ui/Toast';
import { FileSpreadsheet, Search, Filter, Download, Activity } from 'lucide-react';

interface AuditLogItem {
  id: string;
  user_id?: string;
  user_email?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export function AuditLogsPage() {
  const { activeOrg } = useOrg();
  const { toast } = useToast();

  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [actionFilter, setActionFilter] = useState('');

  const fetchAuditLogs = useCallback(async () => {
    if (!activeOrg) return;
    setIsLoading(true);
    try {
      let url = '/audit-logs';
      if (searchQuery.trim()) {
        url = `/audit-logs/search?q=${encodeURIComponent(searchQuery)}`;
      }
      const res = await apiClient.get(url);
      const raw = res.data?.items || res.data?.logs || res.data;
      setLogs(Array.isArray(raw) ? raw : []);

    } catch {
      toast('error', 'Failed to load audit trail');
    } finally {
      setIsLoading(false);
    }
  }, [activeOrg, searchQuery, toast]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchAuditLogs();
    }, 300);
    return () => clearTimeout(timer);
  }, [fetchAuditLogs]);

  const handleExport = () => {
    toast('info', 'Export feature placeholder triggered. Audit trail CSV payload prepared.');
  };

  const filteredLogs = logs.filter((log) => {
    if (!actionFilter) return true;
    return (log.action || '').toLowerCase().includes((actionFilter || '').toLowerCase());
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <FileSpreadsheet className="w-6 h-6 text-amber-400" />
            Audit Log Timeline
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Immutable security audit trail for organization <strong>{activeOrg?.name}</strong>
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={handleExport} leftIcon={<Download className="w-4 h-4" />}>
          Export Audit Trail (CSV)
        </Button>
      </div>

      {/* Search & Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              placeholder="Search audit logs..."
              leftIcon={<Search className="w-4 h-4" />}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Input
              placeholder="Filter by action (e.g. login, upload)..."
              leftIcon={<Filter className="w-4 h-4" />}
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Audit Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Activity Timeline</CardTitle>
          <CardDescription>Chronological log of events</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={5} />
          ) : filteredLogs.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400">No audit events match your query.</div>
          ) : (
            <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
              {filteredLogs.map((item) => (
                <div key={item.id} className="relative flex flex-col gap-1">
                  <div className="absolute -left-[23px] top-0.5 w-3 h-3 rounded-full bg-amber-400 border-2 border-slate-950" />
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-100">{item.action}</span>
                    <Badge variant="purple" size="sm">
                      {item.resource_type}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                    <span>Actor: {item.user_email || item.user_id || 'System'}</span>
                    <span>•</span>
                    <span>{new Date(item.created_at).toLocaleString()}</span>
                  </div>
                  {item.metadata && (
                    <pre className="mt-1 p-2 rounded bg-slate-950 text-[10px] font-mono text-slate-300 overflow-x-auto border border-slate-800">
                      {JSON.stringify(item.metadata, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
