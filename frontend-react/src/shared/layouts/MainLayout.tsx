import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { WifiOff, AlertTriangle } from 'lucide-react';
import { apiClient } from '../api/client';

export function MainLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const isOnline = useOnlineStatus();
  const [healthStatus, setHealthStatus] = useState<string | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await apiClient.get('/health');
        if (res.data?.status === 'degraded') {
          setHealthStatus('System services running in degraded mode (Meilisearch / Email / Redis).');
        } else {
          setHealthStatus(null);
        }
      } catch {
        setHealthStatus('Unable to reach backend API.');
      }
    };
    checkHealth();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      <div className="flex-1 md:pl-64 flex flex-col min-h-screen">
        <Navbar onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} />

        {/* Global Offline Bar */}
        {!isOnline && (
          <div className="bg-amber-500/20 border-b border-amber-500/30 px-4 py-2 text-xs text-amber-200 flex items-center justify-center gap-2">
            <WifiOff className="w-4 h-4 text-amber-400" />
            <span>You are currently offline. Changes will sync when network connectivity is restored.</span>
          </div>
        )}

        {/* Degraded Backend Banner */}
        {isOnline && healthStatus && (
          <div className="bg-sky-500/10 border-b border-sky-500/20 px-4 py-1.5 text-xs text-sky-300 flex items-center justify-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-sky-400" />
            <span>{healthStatus}</span>
          </div>
        )}

        <main className="flex-1 p-4 md:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
