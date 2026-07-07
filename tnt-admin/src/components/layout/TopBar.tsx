import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Bell, LogOut, User, Search, ChevronDown,
  Activity, AlertTriangle,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useUIStore } from '../../store/uiStore';
import { useEmergencyStatus } from '../../hooks/useEmergencyStatus';
import { cn } from '../../utils/cn';

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/users': 'Users',
  '/vendors': 'Vendors',
  '/orders': 'Orders',
  '/complaints': 'Complaints',
  '/rewards': 'Rewards & Vouchers',
  '/stationery': 'Stationery',
  '/ai': 'AI Intelligence',
  '/ledger': 'Financial Ledger',
  '/announcements': 'Announcements',
  '/policies': 'Policies',
  '/settings': 'Settings',
};

export function TopBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { notificationsCount, sidebarOpen } = useUIStore();
  const { health } = useEmergencyStatus();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const currentTitle = Object.entries(PAGE_TITLES).find(([path]) =>
    location.pathname.startsWith(path)
  )?.[1] || 'Dashboard';

  const isHealthy = health?.status === 'ok';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header
      className={cn(
        'fixed top-0 right-0 h-16 z-20',
        'bg-white border-b border-[#E5E7EB]',
        'flex items-center gap-4 px-6',
        'transition-all duration-300',
        sidebarOpen ? 'left-[260px]' : 'left-[64px]'
      )}
    >
      {/* Page Title */}
      <h1 className="text-base font-semibold shrink-0 text-[#111827]">{currentTitle}</h1>

      {/* Search Bar */}
      <div className="flex-1 max-w-md relative">
        <button
          type="button"
          onClick={() => {
            const evt = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, metaKey: true });
            window.dispatchEvent(evt);
          }}
          className="w-full text-left rounded-[14px] pl-9 pr-4 py-2 text-sm transition-all duration-150 bg-[#F3F5F9] border border-[#E5E7EB] text-[#111827]"
        >
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
          <span className="text-[#9CA3AF]">
            Search orders, users, vendors… <span className="font-mono text-[#9CA3AF]">⌘K</span>
          </span>
        </button>
      </div>

      {/* Right Side Controls */}
      <div className="ml-auto flex items-center gap-2">
        {/* Health Indicator */}
        <div
          className={cn(
            'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium',
            isHealthy
              ? 'bg-green-50 text-green-600'
              : 'bg-red-50 text-red-600'
          )}
          title={`Backend: ${health?.status || 'checking...'} | DB: ${health?.db || '?'} | Redis: ${health?.redis || '?'}`}
        >
          {isHealthy ? (
            <>
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              <Activity className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Live</span>
            </>
          ) : (
            <>
              <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
              <AlertTriangle className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Offline</span>
            </>
          )}
        </div>

        {/* Notifications */}
        <button
          onClick={() => navigate('/announcements')}
          className="w-9 h-9 flex items-center justify-center rounded-lg bg-[#F3F5F9] border border-[#E5E7EB] text-[#6B7280] hover:bg-[#E9EDF5] hover:text-[#111827] transition-all duration-150"
          title="Announcements & Notifications"
        >
          <Bell className="w-4 h-4" />
          {notificationsCount > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[16px] h-4 bg-[#E85D24] text-white text-[10px] rounded-full flex items-center justify-center px-0.5 font-bold">
              {notificationsCount > 9 ? '9+' : notificationsCount}
            </span>
          )}
        </button>

        {/* Avatar Dropdown */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-lg bg-[#F3F5F9] border border-[#E5E7EB] hover:border-[#D1D5DB] transition-all duration-150"
          >
            <div className="w-7 h-7 rounded-full bg-gradient-orange flex items-center justify-center text-white font-bold text-xs">
              {user?.name?.charAt(0)?.toUpperCase() || 'A'}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-xs font-medium text-[#111827] leading-tight">
                {user?.name || 'Admin'}
              </p>
              <p className="text-[10px] text-[#6B7280] leading-tight capitalize">
                {user?.role?.replace('_', ' ')}
              </p>
            </div>
            <ChevronDown className={cn(
              'w-3.5 h-3.5 text-[#6B7280] transition-transform duration-150',
              dropdownOpen && 'rotate-180'
            )} />
          </button>

          {dropdownOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setDropdownOpen(false)}
              />
              <div className="absolute right-0 top-full mt-2 w-48 bg-white border border-[#E5E7EB] rounded-xl shadow-lg z-20 py-1 animate-fade-in">
                <button
                  onClick={() => { navigate('/settings'); setDropdownOpen(false); }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-[#111827] hover:bg-[#F3F5F9] transition-colors"
                >
                  <User className="w-4 h-4 text-[#6B7280]" />
                  Profile & Settings
                </button>
                <div className="border-t border-[#E5E7EB] my-1" />
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}