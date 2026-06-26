import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useUIStore } from '../../store/uiStore';
import { adminApi } from '../../api/admin';
import toast from 'react-hot-toast';

export function EmergencyBanner() {
  const { emergencyShutdown, setEmergencyShutdown } = useUIStore();

  if (!emergencyShutdown) return null;

  const handleResume = async () => {
    try {
      await adminApi.toggleShutdown();
      setEmergencyShutdown(false);
      toast.success('✅ Campus services resumed — students can place orders again');
    } catch {
      toast.error('Failed to resume services. Try again.');
    }
  };

  return (
    <div className="sticky top-16 z-25 w-full flex items-center justify-between gap-4 px-6 py-3"
         style={{
           background: 'rgba(220, 38, 38, 0.12)',
           borderBottom: '1px solid rgba(220, 38, 38, 0.35)',
         }}>
      <div className="flex items-center gap-3">
        <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse shrink-0" />
        <div>
          <p className="font-semibold text-sm text-red-400">⚠ CAMPUS SERVICES SUSPENDED</p>
          <p className="text-xs text-red-400/70 mt-0.5">
            All ordering and booking on the student mobile app is returning 503. Students cannot place orders.
          </p>
        </div>
      </div>
      <button
        onClick={handleResume}
        className="shrink-0 px-4 py-1.5 rounded-lg text-sm font-semibold transition-colors
                   focus:outline-none hover:bg-green-500 hover:text-white"
        style={{ border: '1px solid #22C55E', color: '#22C55E' }}
      >
        Resume Services
      </button>
    </div>
  );
}