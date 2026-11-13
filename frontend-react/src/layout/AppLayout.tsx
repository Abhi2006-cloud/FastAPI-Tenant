import React, { useState } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  LayoutDashboard,
  Users,
  UserPlus,
  FileText,
  Search,
  ShieldAlert,
  CreditCard,
  Settings,
  Server,
  KeyRound,
  LogOut,
  ChevronDown,
  Check,
  Plus,
  Sparkles,
  BookOpen,
} from "lucide-react";
import { useAuth } from "../shared/context/AuthContext.tsx";
import { useOrg } from "../shared/context/OrgContext.tsx";
import { ColdStartBanner } from "../shared/components/ColdStartBanner.tsx";
import { useToast } from "../shared/components/Toast.tsx";

export const AppLayout: React.FC = () => {
  const { user, isDemo, demoExpiresAt, upgradeDemoToPro, logout } = useAuth();
  const { activeOrgId, activeOrg, myOrgs, entitlements, role, switchOrg } = useOrg();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [upgradingDemo, setUpgradingDemo] = useState(false);

  const planName = entitlements?.plan || activeOrg?.plan || "free";

  const handleUpgradeDemo = async () => {
    setUpgradingDemo(true);
    try {
      await upgradeDemoToPro();
      await queryClient.invalidateQueries({ queryKey: ["entitlements"] });
      await queryClient.invalidateQueries({ queryKey: ["my-organizations"] });
      showToast("Demo workspace upgraded to Pro!", "success");
    } catch {
      showToast("Failed to upgrade demo workspace.", "error");
    } finally {
      setUpgradingDemo(false);
    }
  };

  const handleSignOut = async () => {
    await logout();
    navigate("/login");
  };

  const navItems = [
    { label: "Overview", to: `/o/${activeOrgId}/overview`, icon: LayoutDashboard },
    { label: "Members", to: `/o/${activeOrgId}/members`, icon: Users },
    { label: "Invitations", to: `/o/${activeOrgId}/invitations`, icon: UserPlus },
    { label: "Files", to: `/o/${activeOrgId}/files`, icon: FileText },
    { label: "Search", to: `/o/${activeOrgId}/search`, icon: Search },
    { label: "Audit Logs", to: `/o/${activeOrgId}/audit`, icon: ShieldAlert },
    { label: "Billing & Plans", to: `/o/${activeOrgId}/billing`, icon: CreditCard },
    { label: "Settings", to: `/o/${activeOrgId}/settings`, icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col text-[#18181B]">
      {/* 1. Cold Start Wake Banner */}
      <ColdStartBanner />

      {/* 2. Demo Banner if in Demo account */}
      {isDemo && (
        <div className="bg-[#F0FDFA] border-b border-[#CCFBF1] text-[#115E59] px-4 py-1.5 text-[12px] flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[#0F766E]" />
            <span>
              Demo workspace
              {demoExpiresAt ? ` (expires ${new Date(demoExpiresAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})` : ""}
            </span>
          </div>
          <button
            type="button"
            disabled={upgradingDemo}
            onClick={handleUpgradeDemo}
            className="px-2.5 py-0.5 bg-[#0F766E] hover:bg-[#115E59] text-white font-medium rounded text-[11px] disabled:opacity-50"
          >
            {upgradingDemo ? "Upgrading..." : "Switch demo to Pro"}
          </button>
        </div>
      )}

      {/* 3. Top Bar */}
      <header className="h-12 bg-white border-b border-[#E4E4E7] px-4 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-3">
          {/* Organization Switcher Dropdown */}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button
                type="button"
                className="flex items-center gap-2 px-2.5 py-1 text-[13px] font-medium border border-[#E4E4E7] rounded-[6px] hover:bg-[#FAFAFA] focus:outline-none"
              >
                <span className="max-w-[140px] truncate">{activeOrg?.name || "Select Workspace"}</span>
                <ChevronDown className="w-3.5 h-3.5 text-[#71717A]" />
              </button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                align="start"
                className="w-56 bg-white border border-[#E4E4E7] rounded-[6px] shadow-md p-1 z-50 text-[13px] focus:outline-none"
              >
                <div className="px-2 py-1.5 text-[11px] font-semibold text-[#71717A] uppercase tracking-wider">
                  Workspaces
                </div>
                {myOrgs.map((org) => (
                  <DropdownMenu.Item
                    key={org.id}
                    onClick={() => switchOrg(org.id)}
                    className="flex items-center justify-between px-2.5 py-1.5 rounded-[4px] cursor-pointer hover:bg-[#F4F4F5] focus:bg-[#F4F4F5] focus:outline-none"
                  >
                    <div className="truncate">
                      <span className="text-[#18181B] font-medium">{org.name}</span>
                      <span className="ml-2 text-[11px] text-[#71717A] capitalize">({org.role || "member"})</span>
                    </div>
                    {org.id === activeOrgId && <Check className="w-3.5 h-3.5 text-[#0F766E]" />}
                  </DropdownMenu.Item>
                ))}
                <DropdownMenu.Separator className="h-px bg-[#E4E4E7] my-1" />
                <DropdownMenu.Item
                  onClick={() => navigate("/o/new")}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-[4px] cursor-pointer text-[#0F766E] hover:bg-[#F0FDFA] focus:bg-[#F0FDFA] focus:outline-none"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create Workspace</span>
                </DropdownMenu.Item>
                <DropdownMenu.Item
                  onClick={() => navigate("/invitations")}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-[4px] cursor-pointer text-[#52525B] hover:bg-[#F4F4F5] focus:bg-[#F4F4F5] focus:outline-none"
                >
                  <KeyRound className="w-3.5 h-3.5 text-[#0F766E]" />
                  <span>Join with Invite Token</span>
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>

          {/* Plan Badge */}
          <span className="px-2 py-0.5 text-[11px] font-medium tracking-wide uppercase bg-[#F4F4F5] text-[#52525B] border border-[#E4E4E7] rounded-[4px]">
            {planName}
          </span>
          {role && (
            <span className="text-[12px] text-[#71717A] capitalize">
              {role}
            </span>
          )}
        </div>

        {/* User Menu Dropdown */}
        <div className="flex items-center gap-3">
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button
                type="button"
                className="flex items-center gap-2 text-[13px] text-[#52525B] hover:text-[#18181B] px-2 py-1 rounded hover:bg-[#FAFAFA] focus:outline-none"
              >
                <div className="w-6 h-6 rounded-full bg-[#E4E4E7] flex items-center justify-center text-[11px] font-semibold text-[#18181B]">
                  {user?.email?.charAt(0).toUpperCase() || "U"}
                </div>
                <span className="max-w-[150px] truncate">{user?.email}</span>
                <ChevronDown className="w-3 h-3 text-[#71717A]" />
              </button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                align="end"
                className="w-48 bg-white border border-[#E4E4E7] rounded-[6px] shadow-md p-1 z-50 text-[13px] focus:outline-none"
              >
                <div className="px-2 py-1 text-[11px] text-[#71717A] border-b border-[#E4E4E7] mb-1 truncate">
                  {user?.email}
                </div>
                <DropdownMenu.Item
                  onClick={() => navigate("/account/security")}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-[4px] cursor-pointer hover:bg-[#F4F4F5] focus:bg-[#F4F4F5] focus:outline-none text-[#18181B]"
                >
                  <KeyRound className="w-3.5 h-3.5 text-[#71717A]" />
                  <span>Security & Sessions</span>
                </DropdownMenu.Item>
                <DropdownMenu.Item
                  onClick={() => navigate("/platform")}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-[4px] cursor-pointer hover:bg-[#F4F4F5] focus:bg-[#F4F4F5] focus:outline-none text-[#18181B]"
                >
                  <Server className="w-3.5 h-3.5 text-[#71717A]" />
                  <span>Platform Architecture</span>
                </DropdownMenu.Item>
                <DropdownMenu.Separator className="h-px bg-[#E4E4E7] my-1" />
                <DropdownMenu.Item
                  onClick={handleSignOut}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-[4px] cursor-pointer hover:bg-[#FEF2F2] focus:bg-[#FEF2F2] focus:outline-none text-[#DC2626]"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out</span>
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </header>

      {/* 4. Body (Sidebar + Content) */}
      <div className="flex-1 flex">
        {/* Left Sidebar: 232px */}
        <aside className="w-[232px] bg-white border-r border-[#E4E4E7] flex flex-col justify-between py-4 shrink-0">
          <nav className="space-y-0.5 px-2">
            <div className="px-2 py-1 text-[11px] font-semibold text-[#71717A] uppercase tracking-wider">
              Workspace
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.label}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-2.5 py-1.5 rounded-[6px] text-[13px] font-medium transition-colors ${isActive
                      ? "bg-[#F0FDFA] text-[#0F766E]"
                      : "text-[#52525B] hover:text-[#18181B] hover:bg-[#F4F4F5]"
                    }`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}

            <div className="pt-4 px-2 py-1 text-[11px] font-semibold text-[#71717A] uppercase tracking-wider">
              Platform & Docs
            </div>
            <NavLink
              to="/platform"
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-2.5 py-1.5 rounded-[6px] text-[13px] font-medium transition-colors ${isActive
                  ? "bg-[#F0FDFA] text-[#0F766E]"
                  : "text-[#52525B] hover:text-[#18181B] hover:bg-[#F4F4F5]"
                }`
              }
            >
              <Server className="w-4 h-4 shrink-0" />
              <span>Platform Status</span>
            </NavLink>
            <NavLink
              to="/docs/search"
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-2.5 py-1.5 rounded-[6px] text-[13px] font-medium transition-colors ${isActive
                  ? "bg-[#F0FDFA] text-[#0F766E]"
                  : "text-[#52525B] hover:text-[#18181B] hover:bg-[#F4F4F5]"
                }`
              }
            >
              <BookOpen className="w-4 h-4 shrink-0" />
              <span>Search Architecture</span>
            </NavLink>
            <NavLink
              to="/docs/email"
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-2.5 py-1.5 rounded-[6px] text-[13px] font-medium transition-colors ${isActive
                  ? "bg-[#F0FDFA] text-[#0F766E]"
                  : "text-[#52525B] hover:text-[#18181B] hover:bg-[#F4F4F5]"
                }`
              }
            >
              <BookOpen className="w-4 h-4 shrink-0" />
              <span>Email Architecture</span>
            </NavLink>
          </nav>

          <div className="px-4 text-[11px] text-[#71717A]">
            v2.5.0 • Zero-Cost Tier
          </div>
        </aside>

        {/* Content Area: Max-Width 1120px */}
        <main className="flex-1 p-6 flex justify-center overflow-y-auto">
          <div className="w-full max-w-[1120px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
