import React, { useState, useEffect } from 'react';
import { AlertTriangle, AlertOctagon, Info, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { adminApi } from '../api/admin';
import { cn } from '../utils/cn';

interface ConflictTotals {
  critical: number;
  high: number;
  medium: number;
}

const SEVERITY_CONFIG: Record<string, { label: string; icon: React.ElementType; bg: string; border: string; text: string }> = {
  critical: {
    label: 'Overbooked',
    icon: AlertOctagon,
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-700',
  },
  high: {
    label: 'Duplicate Bookings',
    icon: AlertTriangle,
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-700',
  },
  medium: {
    label: 'Near Capacity',
    icon: Info,
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-700',
  },
};

export default function ConflictWidget() {
  const navigate = useNavigate();
  const [totals, setTotals] = useState<ConflictTotals>({ critical: 0, high: 0, medium: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await adminApi.getConflicts();
        setTotals(res.data?.totals || { critical: 0, high: 0, medium: 0 });
      } catch {
        // silent
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="tnt-card h-32 animate-pulse" />;
  }

  const hasIssues = Object.values(totals).some((v) => v > 0);

  return (
    <div className="tnt-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <h3 className="text-sm font-semibold text-[#111827]">Slot Conflicts</h3>
        </div>
        {hasIssues && (
          <button
            onClick={() => navigate('/conflicts')}
            className="flex items-center gap-1 text-xs text-[#4F46E5] hover:text-[#111827]"
          >
            View all <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>

      {!hasIssues ? (
        <div className="flex items-center gap-2 text-sm text-green-600">
          <div className="h-2 w-2 rounded-full bg-green-400" />
          All slots operating normally
        </div>
      ) : (
        <div className="space-y-2">
          {(Object.entries(SEVERITY_CONFIG) as [string, typeof SEVERITY_CONFIG[string]][]).map(([key, cfg]) => {
            const count = totals[key as keyof ConflictTotals];
            if (count === 0) return null;
            const Icon = cfg.icon;
            return (
              <div
                key={key}
                className={cn('flex items-center justify-between rounded-lg border px-3 py-2', cfg.bg, cfg.border)}
              >
                <div className="flex items-center gap-2">
                  <Icon className={cn('w-4 h-4', cfg.text)} />
                  <span className={cn('text-xs font-medium', cfg.text)}>{cfg.label}</span>
                </div>
                <span className={cn('text-sm font-bold', cfg.text)}>{count}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}