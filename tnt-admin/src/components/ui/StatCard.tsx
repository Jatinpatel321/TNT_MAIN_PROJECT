import React, { useEffect, useRef, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '../../utils/cn';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: number;
  loading?: boolean;
  accent?: 'indigo' | 'blue' | 'green' | 'amber' | 'red';
}

const ACCENT_STYLES = {
  indigo: { icon: '#4F46E5', glow: 'rgba(79,70,229,0.08)', border: 'rgba(79,70,229,0.15)' },
  blue:   { icon: '#2563EB', glow: 'rgba(37,99,235,0.08)', border: 'rgba(37,99,235,0.15)' },
  green:  { icon: '#22C55E', glow: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.15)' },
  amber:  { icon: '#F59E0B', glow: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.15)' },
  red:    { icon: '#EF4444', glow: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.15)' },
};

function useCountUp(target: string | number, duration = 500): string | number {
  const [display, setDisplay] = useState<string | number>(0);
  const rafRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    const raw = typeof target === 'number'
      ? target
      : parseFloat(String(target).replace(/[^0-9.]/g, ''));

    if (isNaN(raw) || typeof target === 'string') {
      const t = setTimeout(() => setDisplay(target), 50);
      return () => clearTimeout(t);
    }

    const startVal = 0;
    startTimeRef.current = null;

    const step = (timestamp: number) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;
      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(startVal + eased * (raw - startVal));
      setDisplay(current.toLocaleString('en-IN'));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        setDisplay(raw.toLocaleString('en-IN'));
      }
    };

    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(step);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [target, duration]);

  return display;
}

export function StatCard({
  title, value, subtitle, icon: Icon, trend, loading = false, accent = 'indigo',
}: StatCardProps) {
  const styles = ACCENT_STYLES[accent];
  const animatedValue = useCountUp(value);

  if (loading) {
    return (
      <div className="stat-card">
        <div className="flex items-start justify-between mb-4">
          <div className="skeleton w-10 h-10 rounded-lg" />
          <div className="skeleton w-16 h-5 rounded-full" />
        </div>
        <div className="skeleton w-24 h-7 rounded mb-2" />
        <div className="skeleton w-32 h-4 rounded" />
      </div>
    );
  }

  return (
    <div className="stat-card group cursor-default" style={{
      '--accent-color': styles.icon,
      '--accent-glow': styles.glow,
      '--accent-border': styles.border,
    } as React.CSSProperties}>
      {/* Accent glow */}
      <div className="absolute top-0 right-0 w-32 h-32 rounded-full opacity-40 blur-3xl pointer-events-none"
        style={{ background: styles.glow }} />
      
      <div className="relative z-10">
        <div className="flex items-start justify-between mb-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: styles.glow, color: styles.icon }}>
            <Icon className="w-5 h-5" />
          </div>

          {trend !== undefined && (
            <div className={cn(
              'flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
              trend > 0 ? 'text-green-600' :
              trend < 0 ? 'text-red-600' :
              'text-[#9CA3AF]'
            )} style={{
              background: trend > 0 ? 'rgba(34,197,94,0.1)' : trend < 0 ? 'rgba(239,68,68,0.1)' : 'var(--bg-elevated)',
            }}>
              {trend > 0 ? <TrendingUp className="w-3 h-3" /> :
               trend < 0 ? <TrendingDown className="w-3 h-3" /> :
               <Minus className="w-3 h-3" />}
              <span>{Math.abs(trend).toFixed(1)}%</span>
            </div>
          )}
        </div>

        <div className="mt-2">
          <p className="text-2xl font-bold leading-none tracking-tight font-mono text-[#111827]">
            {animatedValue}
          </p>
          <p className="text-sm mt-1 font-medium text-[#4B5563]">{title}</p>
          {subtitle && (
            <p className="text-xs mt-1 text-[#9CA3AF]">{subtitle}</p>
          )}
        </div>
      </div>
    </div>
  );
}