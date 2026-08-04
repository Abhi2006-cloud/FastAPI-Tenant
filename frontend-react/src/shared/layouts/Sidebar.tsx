import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  Users,
  FolderKanban,
  Search,
  ShieldCheck,
  Mail,
  FileSpreadsheet,
  Activity,
  UserCheck,
} from 'lucide-react';
import { cn } from '../utils/cn';

interface SidebarProps {
  isOpen: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen }: SidebarProps) {
  const links = [
    { label: 'Dashboard', to: '/', icon: LayoutDashboard },
    { label: 'Organizations', to: '/organizations', icon: Building2 },
    { label: 'Team Members', to: '/members', icon: Users },
    { label: 'File Manager', to: '/files', icon: FolderKanban },
    { label: 'Global Search', to: '/search', icon: Search },
    { label: 'Sessions & Security', to: '/sessions', icon: ShieldCheck },
    { label: 'Email Infrastructure', to: '/email', icon: Mail },
    { label: 'Audit Logs', to: '/audit', icon: FileSpreadsheet },
    { label: 'Worker & Jobs', to: '/jobs', icon: Activity },
    { label: 'User Profile', to: '/profile', icon: UserCheck },
  ];

  return (
    <aside
      className={cn(
        'fixed top-0 left-0 z-40 h-screen w-64 bg-slate-900/90 border-r border-slate-800 backdrop-blur-xl transition-transform duration-300 md:translate-x-0 flex flex-col justify-between p-4',
        !isOpen && '-translate-x-full'
      )}
    >
      <div>
        <div className="flex items-center gap-3 px-3 py-4 border-b border-slate-800 mb-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
            FT
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 tracking-tight">FastAPI Tenant</h2>
            <span className="text-[10px] text-blue-400 font-mono">React v2.4.0</span>
          </div>
        </div>

        <nav className="space-y-1">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all duration-150',
                    isActive
                      ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  )
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{link.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="pt-4 border-t border-slate-800 text-[11px] text-slate-400 text-center">
        <p>Tenant SaaS Ecosystem</p>
        <p className="text-[9px] text-slate-400 font-mono mt-0.5">REST API Connected</p>
      </div>
    </aside>
  );
}
