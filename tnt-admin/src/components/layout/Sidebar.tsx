import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Users, Store, ShoppingBag, MessageSquareWarning,
  Gift, Printer, Brain, BookOpen, Megaphone, Shield, Settings,
  ChevronLeft, ChevronRight, Zap, Activity, ClipboardList, Siren, Database, AlertTriangle, ShieldCheck, ShieldAlert
} from 'lucide-react';
import logo from '../../assets/TAP N TAKE_page-0001 (1).jpg';
import { useUIStore } from '../../store/uiStore';
import { useAuthStore } from '../../store/authStore';
import { cn } from '../../utils/cn';
import { adminApi } from '../../api/admin';
import { complaintsApi } from '../../api/complaints';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/users', label: 'Users', icon: Users },
  { path: '/vendors', label: 'Vendors', icon: Store, badge: 'pendingVendors' as const },
  { path: '/orders', label: 'Orders', icon: ShoppingBag },
  { path: '/complaints', label: 'Complaints', icon: MessageSquareWarning, badge: 'openComplaints' as const },
  { path: '/rewards', label: 'Rewards', icon: Gift },
  { path: '/stationery', label: 'Stationery', icon: Printer },
  { path: '/ai', label: 'AI Intelligence', icon: Brain },
  { path: '/ledger', label: 'Ledger', icon: BookOpen },
  { path: '/announcements', label: 'Announcements', icon: Megaphone },
  { path: '/audit-logs', label: 'Audit Logs', icon: ClipboardList },
  { path: '/conflicts', label: 'Conflicts', icon: Siren },
  { path: '/fraud', label: 'Fraud Alerts', icon: AlertTriangle },
  { path: '/security', label: 'Security SOC', icon: ShieldAlert },
  { path: '/backup', label: 'Backup & Recovery', icon: ShieldCheck },
  { path: '/policies', label: 'Policies', icon: Shield },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const {
    sidebarOpen,
    toggleSidebar,
    pendingVendorsCount,
    openComplaintsCount,
    setPendingVendorsCount,
    setOpenComplaintsCount,
  } = useUIStore();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  const getBadgeCount = (badge?: 'pendingVendors' | 'openComplaints') => {
    if (badge === 'pendingVendors') return pendingVendorsCount;
    if (badge === 'openComplaints') return openComplaintsCount;
    return 0;
  };

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const [vendorsRes, complaintsRes] = await Promise.allSettled([
          adminApi.getPendingVendors(),
          complaintsApi.getAll({ status: 'open', limit: 5 }),
        ]);

        if (!alive) return;

        if (vendorsRes.status === 'fulfilled') {
          const list = Array.isArray(vendorsRes.value.data) ? vendorsRes.value.data : [];
          setPendingVendorsCount(list.length);
        }
        if (complaintsRes.status === 'fulfilled') {
          const list = Array.isArray(complaintsRes.value.data) ? complaintsRes.value.data : [];
          setOpenComplaintsCount(list.length);
        }
      } catch {
        // keep last values
      }
    };

    poll();
    const interval = setInterval(poll, 60_000);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [setPendingVendorsCount, setOpenComplaintsCount]);

  useEffect(() => {
    let alive = true;
    const pollHealth = async () => {
      try {
        const res = await adminApi.getHealth();
        if (!alive) return;
        setBackendHealthy(res.data?.status === 'ok' && !res.data?.shutdown_active);
      } catch {
        if (!alive) return;
        setBackendHealthy(false);
      }
    };

    pollHealth();
    const interval = setInterval(pollHealth, 10_000);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 h-screen z-30 flex flex-col bg-white',
        'border-r border-[#E5E7EB]',
        'transition-[width] duration-300 ease-in-out',
        sidebarOpen ? 'w-[260px]' : 'w-[64px]',
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-[#E5E7EB] shrink-0">
        <img src={logo} alt="TAP N TAKE Logo" className="w-9 h-9 rounded-full object-cover shrink-0" />
        {sidebarOpen && (
          <div className="overflow-hidden">
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg leading-none text-[#111827]">TNT</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-[rgba(232,93,36,0.10)] text-[#E85D24] border border-[#E85D24]">
                ADMIN
              </span>
            </div>
            <p className="text-[10px] mt-0.5 text-[#6B7280]">Tap N Take</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const badgeCount = 'badge' in item ? getBadgeCount(item.badge) : 0;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  'nav-item',
                  isActive && 'active',
                  !sidebarOpen && 'justify-center px-2'
                )
              }
              title={!sidebarOpen ? item.label : undefined}
            >
              <div className="relative shrink-0">
                <Icon className={cn('w-5 h-5', 'text-[#6B7280]', 'group-[.active]:text-[#4F46E5]')} />
                {badgeCount > 0 && !sidebarOpen && (
                  <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 bg-[#E85D24] text-white text-[10px] rounded-full flex items-center justify-center px-0.5 font-bold">
                    {badgeCount > 99 ? '99+' : badgeCount}
                  </span>
                )}
              </div>
              {sidebarOpen && (
                <>
                  <span className="flex-1 truncate">{item.label}</span>
                  {badgeCount > 0 && (
                    <span className="min-w-[20px] h-5 bg-[#E85D24] text-white text-[10px] rounded-full flex items-center justify-center px-1.5 font-bold shrink-0">
                      {badgeCount > 99 ? '99+' : badgeCount}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="shrink-0 border-t border-[#E5E7EB]">
        {sidebarOpen && user && (
          <div className="px-3 py-3">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-full bg-gradient-orange flex items-center justify-center text-white font-bold text-sm shrink-0">
                {user.name?.charAt(0)?.toUpperCase() || 'A'}
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="text-sm font-medium truncate text-[#111827]">{user.name || 'Admin'}</p>
                <p className="text-xs capitalize text-[#4B5563]">{user.role?.replace('_', ' ')}</p>
              </div>
            </div>
          </div>
        )}

        {/* Backend health */}
        <div className={cn('px-2 py-2', sidebarOpen ? '' : 'px-0')}>
          <div className={cn(
            'w-full flex items-center gap-2 rounded-xl px-3 py-2 border border-[#E5E7EB]',
          )}>
            <Activity className={cn('w-4 h-4', backendHealthy ? 'text-green-500' : 'text-red-500')} />
            {sidebarOpen ? (
              <div className="flex-1">
                <p className="text-xs font-semibold text-[#111827]">Backend</p>
                <p className="text-[10px] text-[#6B7280]">
                  {backendHealthy === null ? 'checking…' : backendHealthy ? 'healthy' : 'degraded'}
                </p>
              </div>
            ) : (
              <span className={cn('w-2 h-2 rounded-full', backendHealthy ? 'bg-green-500' : 'bg-red-500')} />
            )}
          </div>
        </div>

        {/* Collapse */}
        <div className="px-2 pb-3">
          <button
            onClick={toggleSidebar}
            className={cn('nav-item w-full', !sidebarOpen && 'justify-center px-2')}
            title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {sidebarOpen ? (
              <>
                <ChevronLeft className="w-4 h-4 shrink-0 text-[#6B7280]" />
                <span className="flex-1 text-left text-[#6B7280]">Collapse</span>
              </>
            ) : (
              <ChevronRight className="w-4 h-4 text-[#6B7280]" />
            )}
          </button>
        </div>
      </div>
    </aside>
  );
}
