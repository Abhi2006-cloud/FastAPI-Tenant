import React, { useState } from 'react';
import { useAuth } from '../../features/auth/context/AuthContext';
import { useOrg } from '../../features/organizations/context/OrgContext';
import { useTheme } from '../hooks/useTheme';
import { Building2, Sun, Moon, Laptop, LogOut, ChevronDown, UserCheck, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface NavbarProps {
  onToggleSidebar: () => void;
}

export function Navbar({ onToggleSidebar }: NavbarProps) {
  const { user, logout } = useAuth();
  const { organizations, activeOrg, selectOrg } = useOrg();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();

  const [isOrgDropdownOpen, setIsOrgDropdownOpen] = useState(false);
  const [isUserDropdownOpen, setIsUserDropdownOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-4 md:px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="md:hidden text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Organization Switcher Dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsOrgDropdownOpen(!isOrgDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-slate-800/60 text-xs font-semibold text-slate-200 transition-colors"
          >
            <Building2 className="w-4 h-4 text-blue-400 shrink-0" />
            <span className="truncate max-w-[140px] md:max-w-[200px]">
              {activeOrg ? activeOrg.name : 'Select Organization'}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-1" />
          </button>

          {isOrgDropdownOpen && (
            <div
              className="absolute left-0 mt-2 w-56 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl py-1.5 z-50"
              onClick={() => setIsOrgDropdownOpen(false)}
            >
              <div className="px-3 py-1.5 text-[10px] uppercase font-bold text-slate-400 border-b border-slate-800">
                Your Organizations
              </div>
              <div className="max-h-48 overflow-y-auto">
                {organizations.map((org) => (
                  <button
                    key={org.id}
                    onClick={() => selectOrg(org.id)}
                    className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-slate-800 ${
                      activeOrg?.id === org.id ? 'text-blue-400 font-semibold bg-blue-950/30' : 'text-slate-300'
                    }`}
                  >
                    <span className="truncate">{org.name}</span>
                    {activeOrg?.id === org.id && <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />}
                  </button>
                ))}
              </div>
              <div className="border-t border-slate-800 pt-1 mt-1 space-y-0.5">
                <button
                  onClick={() => navigate('/invitations')}
                  className="w-full text-left px-3 py-1.5 text-xs text-emerald-400 hover:bg-slate-800 font-medium"
                >
                  + Join via Invitation Link
                </button>
                <button
                  onClick={() => navigate('/organizations')}
                  className="w-full text-left px-3 py-1.5 text-xs text-blue-400 hover:bg-slate-800 font-medium"
                >
                  ⚙ Manage Organizations
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Theme Selector */}
        <div className="flex items-center bg-slate-950/60 border border-slate-800 rounded-lg p-0.5">
          <button
            onClick={() => setTheme('light')}
            className={`p-1.5 rounded-md text-xs transition-colors ${theme === 'light' ? 'bg-slate-800 text-amber-400' : 'text-slate-400 hover:text-slate-200'}`}
            title="Light Theme"
          >
            <Sun className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setTheme('dark')}
            className={`p-1.5 rounded-md text-xs transition-colors ${theme === 'dark' ? 'bg-slate-800 text-blue-400' : 'text-slate-400 hover:text-slate-200'}`}
            title="Dark Theme"
          >
            <Moon className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setTheme('system')}
            className={`p-1.5 rounded-md text-xs transition-colors ${theme === 'system' ? 'bg-slate-800 text-slate-200' : 'text-slate-400 hover:text-slate-200'}`}
            title="System Theme"
          >
            <Laptop className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* User Profile Menu */}
        <div className="relative">
          <button
            onClick={() => setIsUserDropdownOpen(!isUserDropdownOpen)}
            className="flex items-center gap-2 pl-2 pr-3 py-1 rounded-full border border-slate-800 bg-slate-950/60 hover:bg-slate-800/60 text-xs text-slate-200 transition-colors"
          >
            <div className="w-6 h-6 rounded-full bg-blue-600/30 border border-blue-500/40 text-blue-400 font-bold flex items-center justify-center text-[10px]">
              {user?.email?.[0]?.toUpperCase() || 'U'}
            </div>
            <span className="truncate max-w-[120px] font-medium hidden sm:inline">{user?.email}</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          </button>

          {isUserDropdownOpen && (
            <div
              className="absolute right-0 mt-2 w-48 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl py-1 z-50 text-xs"
              onClick={() => setIsUserDropdownOpen(false)}
            >
              <div className="px-3 py-2 border-b border-slate-800">
                <p className="font-semibold text-slate-100 truncate">{user?.email}</p>
                <p className="text-[10px] text-slate-400">Authenticated User</p>
              </div>

              <button
                onClick={() => navigate('/profile')}
                className="w-full text-left px-3 py-2 text-slate-300 hover:bg-slate-800 flex items-center gap-2"
              >
                <UserCheck className="w-3.5 h-3.5 text-slate-400" />
                Profile Settings
              </button>

              <button
                onClick={logout}
                className="w-full text-left px-3 py-2 text-rose-400 hover:bg-slate-800 flex items-center gap-2 border-t border-slate-800"
              >
                <LogOut className="w-3.5 h-3.5 text-rose-400" />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
