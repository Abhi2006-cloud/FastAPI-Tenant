import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../shared/components/ui/Card';
import { Badge } from '../../../shared/components/ui/Badge';
import { Button } from '../../../shared/components/ui/Button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../../shared/components/ui/Table';
import { TableSkeleton } from '../../../shared/components/ui/Skeleton';
import { Activity, RefreshCw, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

interface JobItem {
  job_id: string;
  task_name: string;
  status: string;
  created_at: string;
  completed_at?: string;
  error?: string;
}

export function JobsPage() {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [healthInfo, setHealthInfo] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchJobsData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [jobsRes, healthRes] = await Promise.all([
        apiClient.get('/jobs'),
        apiClient.get('/health'),
      ]);
      const raw = jobsRes.data?.jobs || jobsRes.data?.items || jobsRes.data;
      setJobs(Array.isArray(raw) ? raw : []);
      setHealthInfo(healthRes.data);
    } catch {
      // Fallback
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobsData();
  }, [fetchJobsData]);

  const workers = (healthInfo?.workers as { workers?: string[] })?.workers || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Activity className="w-6 h-6 text-purple-400" />
            Background Workers & Job Queue
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Asynchronous background job monitor powered by Redis and Python workers
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={fetchJobsData} leftIcon={<RefreshCw className="w-3.5 h-3.5" />}>
          Refresh Queue
        </Button>
      </div>

      {/* Workers Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-slate-400">Worker Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-slate-100 capitalize">
              {String(healthInfo?.worker || 'unknown')}
            </div>
            <Badge variant="purple" size="sm" className="mt-1">
              Active Workers: {workers.length}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-slate-400">Total Enqueued Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-purple-400">{jobs.length}</div>
            <p className="text-[11px] text-slate-400 mt-1">Processed background tasks</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-slate-400">Redis Broker</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-emerald-400 capitalize">
              {String(healthInfo?.redis || 'connected')}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Message queue state</p>
          </CardContent>
        </Card>
      </div>

      {/* Jobs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Background Jobs</CardTitle>
          <CardDescription>Live execution status of email jobs and async tasks</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={4} />
          ) : jobs.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400">No background jobs in queue history.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job ID</TableHead>
                  <TableHead>Task Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow key={job.job_id}>
                    <TableCell className="font-mono text-xs text-blue-400">{job.job_id}</TableCell>
                    <TableCell className="text-xs text-slate-200 font-medium">{job.task_name}</TableCell>
                    <TableCell>
                      {job.status === 'completed' && (
                        <Badge variant="success" size="sm" className="gap-1">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Completed
                        </Badge>
                      )}
                      {job.status === 'failed' && (
                        <Badge variant="danger" size="sm" className="gap-1">
                          <AlertCircle className="w-3 h-3 text-rose-400" /> Failed
                        </Badge>
                      )}
                      {job.status !== 'completed' && job.status !== 'failed' && (
                        <Badge variant="warning" size="sm" className="gap-1">
                          <Clock className="w-3 h-3 text-amber-400" /> {job.status}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {new Date(job.created_at).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
