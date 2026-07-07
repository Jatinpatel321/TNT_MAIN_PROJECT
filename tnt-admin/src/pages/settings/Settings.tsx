import React, { useState } from 'react';
import {
  User, Phone, Shield, AlertTriangle, CheckCircle,
  Database, Server, Wifi, WifiOff, Power, X, Sun,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../../store/authStore';
import { useUIStore } from '../../store/uiStore';
import { useEmergencyStatus } from '../../hooks/useEmergencyStatus';
import { adminApi } from '../../api/admin';
import { formatPhone } from '../../utils/format';
import { cn } from '../../utils/cn';

export default function Settings() {
  const { user, logout } = useAuthStore();
  const { emergencyShutdown, setEmergencyShutdown } = useUIStore();
  const { health } = useEmergencyStatus();

  const [shutdownConfirm, setShutdownConfirm] = useState(false);
  const [shutdownLoading, setShutdownLoading] = useState(false);

  const handleToggleShutdown = async () => {
    setShutdownLoading(true);
    try {
      const nextState = !emergencyShutdown;
      await adminApi.toggleShutdown(nextState);
      setEmergencyShutdown(nextState);
      setShutdownConfirm(false);
      if (nextState) {
        toast.error('⚠️ Campus services suspended — all mobile users affected');
      } else {
        toast.success('✅ Campus services resumed successfully');
      }
    } catch {
      toast.error('Failed to toggle shutdown. Please try again.');
    } finally {
      setShutdownLoading(false);
    }
  };

  const HealthDot = ({ status }: { status: 'ok' | 'error' | undefined }) => (
    <div className={cn(
      'w-2.5 h-2.5 rounded-full shrink-0',
      status === 'ok' ? 'bg-green-500 animate-pulse' : status === 'error' ? 'bg-red-500' : 'bg-gray-300'
    )} />
  );

  return (
    <div className="max-w-2xl space-y-6">
      {/* Admin Profile */}
      <div className="tnt-card">
        <h3 className="text-sm font-semibold text-[#111827] mb-5 flex items-center gap-2">
          <User className="w-4 h-4 text-[#4F46E5]" />
          Admin Profile
        </h3>
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-orange flex items-center justify-center text-white font-bold text-2xl shrink-0">
            {user?.name?.charAt(0)?.toUpperCase() || 'A'}
          </div>
          <div>
            <h4 className="text-xl font-bold text-[#111827]">{user?.name || 'Admin'}</h4>
            <div className="flex items-center gap-2 mt-1">
              <Phone className="w-3.5 h-3.5 text-[#9CA3AF]" />
              <span className="text-sm text-[#4B5563] font-mono">{user?.phone ? formatPhone(user.phone) : '—'}</span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Shield className="w-3.5 h-3.5 text-[#9CA3AF]" />
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-50 text-[#E85D24] border border-orange-200 capitalize">
                {user?.role?.replace('_', ' ')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Appearance - Light mode only notice */}
      <div className="tnt-card">
        <h3 className="text-sm font-semibold text-[#111827] mb-4 flex items-center gap-2">
          <Sun className="w-4 h-4 text-amber-500" />
          Appearance
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-[#111827]">Light Mode</p>
            <p className="text-xs text-[#4B5563] mt-0.5">
              TNT Enterprise Light — always clean, always bright
            </p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-50 text-amber-600 border border-amber-200">
            <Sun className="w-4 h-4" />
            <span className="text-xs font-medium">Enterprise Light</span>
          </div>
        </div>
      </div>

      {/* Backend Health */}
      <div className="tnt-card">
        <h3 className="text-sm font-semibold text-[#111827] mb-4 flex items-center gap-2">
          <Server className="w-4 h-4 text-[#4F46E5]" />
          Backend Health
        </h3>
        <div className="space-y-3">
          {[
            {
              label: 'API Server',
              status: health?.status === 'ok' ? 'ok' as const : 'error' as const,
              detail: 'http://localhost:8000',
              icon: Wifi,
            },
            {
              label: 'Database',
              status: health?.db,
              detail: 'PostgreSQL connection',
              icon: Database,
            },
            {
              label: 'Redis Cache',
              status: health?.redis,
              detail: 'Session & realtime data',
              icon: Server,
            },
          ].map(item => {
            const Icon = item.icon;
            return (
              <div key={item.label} className="flex items-center gap-3 p-3 bg-[#F3F5F9] rounded-lg border border-[#E5E7EB]">
                <HealthDot status={item.status} />
                <Icon className="w-4 h-4 text-[#9CA3AF]" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#111827]">{item.label}</p>
                  <p className="text-xs text-[#9CA3AF] font-mono">{item.detail}</p>
                </div>
                <span className={cn(
                  'text-xs font-medium capitalize',
                  item.status === 'ok' ? 'text-green-600' : item.status === 'error' ? 'text-red-600' : 'text-gray-400'
                )}>
                  {item.status || 'Unknown'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Emergency Shutdown */}
      <div className="tnt-card border-red-200">
        <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
          <Power className="w-4 h-4 text-red-500" />
          Emergency Shutdown
        </h3>
        <p className="text-xs text-[#4B5563] mb-4">
          {emergencyShutdown
            ? '⚠️ Campus services are currently SUSPENDED. All mobile app users are blocked from placing orders.'
            : 'Use this to immediately suspend all campus ordering services for all users.'}
        </p>

        <div className={cn(
          'p-4 rounded-lg border mb-4',
          emergencyShutdown
            ? 'bg-red-50 border-red-200'
            : 'bg-[#F3F5F9] border-[#E5E7EB]'
        )}>
          <div className="flex items-center gap-3">
            <div className={cn(
              'w-3 h-3 rounded-full',
              emergencyShutdown ? 'bg-red-500 animate-pulse' : 'bg-green-500'
            )} />
            <span className={cn(
              'text-sm font-medium',
              emergencyShutdown ? 'text-red-600' : 'text-green-600'
            )}>
              {emergencyShutdown ? 'SERVICES SUSPENDED' : 'All systems operational'}
            </span>
          </div>
        </div>

        <button
          onClick={() => setShutdownConfirm(true)}
          className={cn(emergencyShutdown ? 'btn-success' : 'btn-danger', 'w-full justify-center text-base py-3')}
        >
          <Power className="w-5 h-5" />
          {emergencyShutdown ? 'Resume Campus Services' : 'Trigger Emergency Shutdown'}
        </button>
      </div>

      {/* Shutdown Confirmation Modal */}
      {shutdownConfirm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <h3 className="text-lg font-bold text-[#111827]">
                  {emergencyShutdown ? 'Resume Services?' : 'Emergency Shutdown?'}
                </h3>
              </div>
              <button onClick={() => setShutdownConfirm(false)} className="btn-ghost btn-sm">
                <X className="w-4 h-4" />
              </button>
            </div>

            {!emergencyShutdown ? (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-5 text-sm text-red-700">
                <p className="font-bold mb-2">⚠️ This will immediately:</p>
                <ul className="space-y-1 text-xs">
                  <li>• Suspend all campus ordering services</li>
                  <li>• Return 503 error to ALL mobile app API calls</li>
                  <li>• Block new orders, slot bookings, and payments</li>
                  <li>• Affect ALL students and faculty instantly</li>
                </ul>
              </div>
            ) : (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-5 text-sm text-green-700">
                <p>This will restore all campus services and allow students and faculty to resume ordering.</p>
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={() => setShutdownConfirm(false)} className="btn-ghost flex-1 justify-center">
                Cancel
              </button>
              <button
                onClick={handleToggleShutdown}
                disabled={shutdownLoading}
                className={cn(
                  'flex-1 justify-center',
                  emergencyShutdown ? 'btn-success' : 'btn-danger'
                )}
              >
                {shutdownLoading ? 'Processing...' : emergencyShutdown ? 'Resume Services' : 'Suspend Now'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}