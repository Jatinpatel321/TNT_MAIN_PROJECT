import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Brain, Activity, Zap, TrendingUp, TrendingDown, Minus,
  AlertTriangle, CheckCircle, Clock, RefreshCw, Cpu, Target, Sparkles,
} from 'lucide-react';
import { aiApi } from '../../api/ai';
import { type ColumnDef } from '@tanstack/react-table';
import { DataTable } from '../../components/ui/DataTable';
import { RUSH_HOUR_COLORS, POLL_INTERVAL_AI } from '../../utils/constants';
import type { VendorRanking, DemandPlan, SlotSuggestion, ETAMetrics, RushHourSignal } from '../../types';
import { cn } from '../../utils/cn';

type PeakHeatmapProps = {
  slots: SlotSuggestion[];
};

function PeakHeatmap({ slots }: PeakHeatmapProps) {
  const bars = useMemo(() => {
    const safeSlots = Array.isArray(slots) ? slots : [];
    const byTime: Record<string, number[]> = {};

    for (const s of safeSlots) {
      const time = s.slot_time;
      const util = Number(s.utilization_percent);
      if (!time) continue;
      if (!byTime[time]) byTime[time] = [];
      if (Number.isFinite(util)) byTime[time].push(util);
    }

    const timeKeys = Object.keys(byTime).sort((a, b) => a.localeCompare(b));
    return timeKeys.map((t) => {
      const arr = byTime[t];
      const avg = arr.length ? arr.reduce((x, y) => x + y, 0) / arr.length : 0;
      return { time: t, utilization: avg };
    });
  }, [slots]);

  const top = bars.slice(0, 8);

  return (
    <div className="space-y-3">
      {top.length === 0 ? (
        <div className="py-6 text-center text-[#4B5563]">
          No slot utilization data
        </div>
      ) : (
        top.map((b, idx) => {
          const pct = Math.max(0, Math.min(100, b.utilization));
          const isHot = pct >= 80;
          const barColor = isHot ? '#F59E0B' : pct >= 60 ? '#2563EB' : '#E5E7EB';

          return (
            <div key={idx} className="flex items-center gap-3 text-[#4B5563]">
              <div className="w-16 text-xs font-mono text-[#4B5563]">
                {b.time}
              </div>
              <div className="flex-1 h-2.5 bg-[#F3F5F9] rounded-full overflow-hidden border border-[#E5E7EB]">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct}%`, backgroundColor: barColor }}
                />
              </div>
              <div className="w-14 text-right text-xs font-mono text-[#111827]">
                {pct.toFixed(0)}%
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

type PredictionCardProps = {
  title: string;
  value: number;
  hint?: string;
  accent: 'success' | 'warning' | 'danger';
  icon: React.ReactNode;
};

function PredictionCard({ title, value, hint, accent, icon }: PredictionCardProps) {
  const colorVar = accent === 'success' ? '#22C55E' : accent === 'warning' ? '#F59E0B' : '#EF4444';
  return (
    <div
      className="p-4 rounded-xl border border-[#E5E7EB] bg-[#F3F5F9] transition-all duration-300 hover:-translate-y-0.5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: 'rgba(79,70,229,0.10)' }}>
            {icon}
          </div>
          <div>
            <p className="text-xs text-[#4B5563]">{title}</p>
            <p className="text-2xl font-bold font-mono" style={{ color: colorVar }}>{value}</p>
          </div>
        </div>
      </div>
      {hint && <p className="mt-2 text-xs text-[#4B5563]">{hint}</p>}
    </div>
  );
}

export default function AIIntelligence() {
  const [rushHour, setRushHour] = useState<RushHourSignal | null>(null);
  const [rankings, setRankings] = useState<VendorRanking[]>([]);
  const [demandPlans, setDemandPlans] = useState<DemandPlan[]>([]);
  const [slotSuggestions, setSlotSuggestions] = useState<SlotSuggestion[]>([]);
  const [etaMetrics, setETAMetrics] = useState<ETAMetrics[]>([]);

  const [reorderCount, setReorderCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const [predictiveEtaRequest, setPredictiveEtaRequest] = useState<{ slotId: number | null; vendorId: number | null }>({
    slotId: null,
    vendorId: null,
  });

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [rushRes, rankRes, slotRes, reorderRes] = await Promise.allSettled([
        aiApi.getRushHour(),
        aiApi.getVendorRanking(),
        aiApi.getSlotSuggestions(),
        aiApi.getReorderPrompts(),
      ]);
      if (rushRes.status === 'fulfilled') setRushHour(rushRes.value.data);
      if (rankRes.status === 'fulfilled') setRankings(Array.isArray(rankRes.value.data) ? rankRes.value.data : []);
      if (slotRes.status === 'fulfilled') setSlotSuggestions(Array.isArray(slotRes.value.data) ? slotRes.value.data : []);

      if (reorderRes.status === 'fulfilled') {
        const data = Array.isArray(reorderRes.value.data) ? reorderRes.value.data : [];
        setReorderCount(data.length);
      }
      setLastRefresh(new Date());
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, POLL_INTERVAL_AI);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const rushLevel = rushHour?.level || 'low';
  const rushColors = RUSH_HOUR_COLORS[rushLevel];
  const rushPercent = rushLevel === 'critical' ? 100 : rushLevel === 'high' ? 75 : rushLevel === 'medium' ? 50 : 25;

  const demandColumns: ColumnDef<DemandPlan, unknown>[] = [
    {
      accessorKey: 'vendor_name',
      header: 'Vendor',
      cell: ({ row }) => <span className="font-medium text-[#111827]">{row.original.vendor_name}</span>,
    },
    {
      accessorKey: 'predicted_orders',
      header: 'Predicted',
      cell: ({ row }) => (
        <span className="font-mono font-bold text-[#4F46E5]">{row.original.predicted_orders}</span>
      ),
    },
    {
      accessorKey: 'current_capacity',
      header: 'Current Cap',
      cell: ({ row }) => (
        <span className="font-mono text-[#9CA3AF]">{row.original.current_capacity}</span>
      ),
    },
    {
      accessorKey: 'recommended_capacity',
      header: 'Recommended',
      cell: ({ row }) => (
        <span className="font-mono text-blue-600">{row.original.recommended_capacity}</span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const ratio = row.original.predicted_orders / row.original.current_capacity;
        if (ratio > 1) return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-600 border border-red-200">
            <AlertTriangle className="w-3 h-3 mr-1" /> Over Capacity
          </span>
        );
        if (ratio > 0.8) return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-600 border border-amber-200">Near Limit</span>
        );
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-600 border border-green-200">OK</span>;
      },
    },
  ];

  const etaColumns: ColumnDef<ETAMetrics, unknown>[] = [
    {
      accessorKey: 'vendor_name',
      header: 'Vendor',
      cell: ({ row }) => <span className="font-medium text-[#111827]">{row.original.vendor_name}</span>,
    },
    {
      accessorKey: 'avg_predicted_eta',
      header: 'Predicted ETA',
      cell: ({ row }) => (
        <span className="font-mono text-[#111827]">{row.original.avg_predicted_eta} min</span>
      ),
    },
    {
      accessorKey: 'avg_actual_time',
      header: 'Actual Time',
      cell: ({ row }) => (
        <span className="font-mono text-[#111827]">{row.original.avg_actual_time} min</span>
      ),
    },
    {
      accessorKey: 'accuracy_percent',
      header: 'Accuracy',
      cell: ({ row }) => {
        const acc = row.original.accuracy_percent;
        return (
          <div className="flex items-center gap-2">
            <div className="w-16 bg-[#E5E7EB] rounded-full h-1.5">
              <div
                className={cn('h-full rounded-full', acc >= 80 ? 'bg-green-500' : acc >= 60 ? 'bg-amber-500' : 'bg-red-500')}
                style={{ width: `${acc}%` }}
              />
            </div>
            <span className={cn('font-mono text-xs font-bold', acc >= 80 ? 'text-green-600' : acc >= 60 ? 'text-amber-600' : 'text-red-600')}>
              {acc.toFixed(1)}%
            </span>
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
            <Brain className="w-5 h-5 text-[#4F46E5]" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[#111827]">AI Intelligence Dashboard</h2>
            <p className="text-xs text-[#9CA3AF]">
              Auto-refreshes every 60s • Last: {lastRefresh.toLocaleTimeString()}
            </p>
          </div>
        </div>
        <button onClick={fetchAll} disabled={loading} className="btn-ghost">
          <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* ─── Row 1: Signals ─────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Rush Hour */}
        <div className="tnt-card">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-4 h-4 text-[#4F46E5]" />
            <h3 className="text-sm font-semibold text-[#111827]">Campus Rush Level</h3>
          </div>
          {loading ? (
            <div className="skeleton h-24 rounded-lg" />
          ) : rushHour ? (
            <div>
              <div className={cn(
                'inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold mb-4',
                rushColors.bg
              )}>
                <div className="w-2.5 h-2.5 rounded-full animate-pulse" style={{ backgroundColor: rushColors.fill }} />
                <span className={rushColors.text}>{rushLevel.toUpperCase()}</span>
              </div>
              <div className="relative">
                <div className="w-full bg-[#E5E7EB] rounded-full h-3 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${rushPercent}%`, backgroundColor: rushColors.fill }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-[#9CA3AF] mt-1">
                  <span>Low</span><span>Medium</span><span>High</span><span>Critical</span>
                </div>
              </div>
              <p className="text-xs text-[#4B5563] mt-3">
                {rushHour.active_orders} active orders on campus right now
              </p>
            </div>
          ) : (
            <p className="text-[#4B5563] text-sm">No rush hour data</p>
          )}
        </div>

        {/* Slot Suggestions */}
        <div className="tnt-card">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-[#111827]">Underutilized Slots</h3>
          </div>
          {loading ? (
            <div className="space-y-2">{[1, 2, 3].map(i => <div key={i} className="skeleton h-8 rounded" />)}</div>
          ) : slotSuggestions.length === 0 ? (
            <div className="text-center py-4">
              <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
              <p className="text-sm text-[#4B5563]">All slots well utilized</p>
            </div>
          ) : (
            <div className="space-y-2">
              {slotSuggestions.slice(0, 4).map((slot, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs">
                  <span className="text-[#111827] truncate flex-1">{slot.vendor_name}</span>
                  <span className="font-mono text-[#9CA3AF] mx-2">{slot.slot_time}</span>
                  <span className="text-amber-600">{slot.utilization_percent.toFixed(0)}%</span>
                </div>
              ))}
              {slotSuggestions.length > 4 && (
                <p className="text-xs text-[#9CA3AF]">+{slotSuggestions.length - 4} more</p>
              )}
            </div>
          )}
        </div>

        {/* Reorder Prompts */}
        <div className="tnt-card">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-amber-600" />
            <h3 className="text-sm font-semibold text-[#111827]">Reorder Signals</h3>
          </div>
          <div className="text-center py-4">
            <p className="text-5xl font-bold font-mono text-[#4F46E5]">{reorderCount}</p>
            <p className="text-xs text-[#9CA3AF] mt-2">users likely to reorder now</p>
            <div className="mt-4 text-xs text-[#9CA3AF]">
              Based on historical order patterns and time-of-day signals
            </div>
          </div>
        </div>
      </div>

      {/* ─── Row 2: Heatmap + Prediction Cards ───────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Peak Heatmap */}
        <div className="tnt-card lg:col-span-1">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#111827]" />
              <h3 className="text-sm font-semibold text-[#111827]">Peak Heatmap</h3>
            </div>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium text-[#9CA3AF] border border-[#E5E7EB]">
              based on slot utilization
            </span>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="skeleton h-10 rounded-lg" />
              ))}
            </div>
          ) : (
            <PeakHeatmap slots={slotSuggestions} />
          )}
        </div>

        {/* Prediction cards */}
        <div className="tnt-card lg:col-span-2">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-[#111827]" />
              <h3 className="text-sm font-semibold text-[#111827]">Predictions</h3>
            </div>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium text-[#9CA3AF] border border-[#E5E7EB]">
              last refresh: {lastRefresh.toLocaleTimeString()}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <PredictionCard
              title="Vendors Over Capacity"
              value={demandPlans.filter(d => d.predicted_orders > d.current_capacity).length}
              accent="danger"
              icon={<AlertTriangle className="w-4 h-4 text-red-600" />}
              hint="Demand exceeds capacity"
            />
            <PredictionCard
              title="Underutilized Slots"
              value={slotSuggestions.length}
              accent="warning"
              icon={<Clock className="w-4 h-4 text-amber-600" />}
              hint="Lowest utilization windows"
            />
            <PredictionCard
              title="Likely Reorders"
              value={reorderCount}
              accent="success"
              icon={<Sparkles className="w-4 h-4 text-green-600" />}
              hint="Based on time-of-day signals"
            />
          </div>

          <div className="mt-4 p-4 rounded-xl border border-[#E5E7EB] bg-[#F3F5F9]">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-indigo-50 border border-indigo-200">
                <Brain className="w-4 h-4 text-[#4F46E5]" />
              </div>
              <div className="flex-1">
                <p className="text-xs text-[#4B5563]">AI Insights</p>
                <p className="text-sm text-[#111827]">
                  {rushHour
                    ? `Current rush level is ${rushLevel.toUpperCase()}. Prioritize capacity for ${rushPercent}% of the day curve and schedule vendor prompts accordingly.`
                    : 'No rush data yet — predictions will update on the next refresh.'}
                </p>
                <div className="mt-2 text-xs text-[#4B5563]">
                  Suggestions are derived from predicted orders vs capacity, slot utilization, and historical reorder signals.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Row 3: Demand Planning Table ───────────────── */}
      <div className="mt-2">
        <div className="flex items-center gap-2 mb-4">
          <Target className="w-4 h-4 text-[#111827]" />
          <h3 className="text-sm font-semibold text-[#111827]">Demand Planning</h3>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium text-[#9CA3AF] border border-[#E5E7EB]">
            {demandPlans.filter(d => d.predicted_orders > d.current_capacity).length} vendors over capacity
          </span>
        </div>
        <DataTable
          data={demandPlans}
          columns={demandColumns}
          loading={loading}
          emptyMessage="No demand planning data available"
        />
      </div>

      {/* ─── Row 4: Vendor Rankings ──────────────────────── */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-4 h-4 text-[#4F46E5]" />
          <h3 className="text-sm font-semibold text-[#111827]">AI Vendor Rankings</h3>
        </div>
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => <div key={i} className="skeleton h-24 rounded-xl" />)}
          </div>
        ) : rankings.length === 0 ? (
          <div className="tnt-card text-center py-8 text-[#9CA3AF] text-sm">No ranking data available</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {rankings.map((vendor) => (
              <div key={vendor.vendor_id} className="tnt-card hover:border-[#D1D5DB] transition-all">
                <div className="flex items-start gap-3">
                  <div className={cn(
                    'w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shrink-0',
                    vendor.rank === 1 ? 'bg-amber-100 text-amber-700' :
                    vendor.rank === 2 ? 'bg-gray-100 text-gray-600' :
                    vendor.rank === 3 ? 'bg-orange-100 text-orange-700' :
                    'bg-[#F3F5F9] text-[#6B7280]'
                  )}>
                    #{vendor.rank}
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <p className="font-medium text-[#111827] truncate text-sm">{vendor.vendor_name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="font-mono text-[#4F46E5] font-bold">{vendor.score.toFixed(2)}</span>
                      {vendor.trend === 'up' && <TrendingUp className="w-3.5 h-3.5 text-green-600" />}
                      {vendor.trend === 'down' && <TrendingDown className="w-3.5 h-3.5 text-red-600" />}
                      {vendor.trend === 'stable' && <Minus className="w-3.5 h-3.5 text-[#9CA3AF]" />}
                    </div>
                    {vendor.category && (
                      <p className="text-xs text-[#9CA3AF] capitalize">{vendor.category}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ─── Row 5: ETA Accuracy ─────────────────────────── */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Cpu className="w-4 h-4 text-[#4F46E5]" />
          <h3 className="text-sm font-semibold text-[#111827]">ETA Prediction Accuracy</h3>
        </div>
        <DataTable
          data={etaMetrics}
          columns={etaColumns}
          loading={loading}
          emptyMessage="No ETA metrics available"
        />
      </div>
    </div>
  );
}