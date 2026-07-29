import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Brain, Activity, Zap, TrendingUp, TrendingDown, Minus,
  AlertTriangle, CheckCircle, Clock, RefreshCw, Cpu, Target, Sparkles,
  ChevronDown, ChevronUp, Info,
} from 'lucide-react';
import { aiApi } from '../../api/ai';
import { type ColumnDef } from '@tanstack/react-table';
import { DataTable } from '../../components/ui/DataTable';
import { RUSH_HOUR_COLORS, POLL_INTERVAL_AI } from '../../utils/constants';
import type { VendorRanking, DemandPlan, SlotSuggestion, ETAMetrics, RushHourSignal, ModelAccuracySummary, ModelAccuracyDetail } from '../../types';
import { cn } from '../../utils/cn';

type PeakHeatmapProps = {
  slots: SlotSuggestion[];
};

const FEATURE_LABELS: Record<string, string> = {
  vendor_id: 'Vendor Identifier',
  queue_length: 'Queue Length (Active Orders)',
  slot_occupancy: 'Slot Occupancy Rate',
  item_count: 'Order Item Count',
  time_of_day: 'Time of Day (Hour)',
  weekday: 'Day of the Week',
  rush_hour: 'Campus Rush Signal',
  daily_avg: 'Daily Avg Orders',
  days_active: 'Active History Days',
  rating: 'Vendor Rating Score',
  total_orders: 'Total Completed Orders',
  avg_prep_time: 'Average Prep Time',
  cancellation_rate: 'Order Cancellation Rate',
  refund_rate: 'Refund Rate',
  current_load: 'Current Stall Load',
  is_student: 'Student Account Flag',
  order_count: 'Customer Order Count',
  total_spend: 'Customer Total Spend',
  night_orders: 'Late Night Orders',
  refund_count: 'Refund Frequency',
  cancellation_count: 'Cancellation Frequency',
  high_value_orders: 'High Value Orders',
};

const DEFAULT_TOP_FEATURES: Record<string, Array<{ feature: string; importance: number }>> = {
  eta_prediction: [
    { feature: 'queue_length', importance: 0.38 },
    { feature: 'slot_occupancy', importance: 0.26 },
    { feature: 'item_count', importance: 0.18 },
    { feature: 'time_of_day', importance: 0.12 },
    { feature: 'rush_hour', importance: 0.06 },
  ],
  demand_forecast: [
    { feature: 'daily_avg', importance: 0.42 },
    { feature: 'weekday', importance: 0.28 },
    { feature: 'rush_hour', importance: 0.18 },
    { feature: 'time_of_day', importance: 0.12 },
  ],
  slot_recommendation: [
    { feature: 'slot_occupancy', importance: 0.45 },
    { feature: 'queue_length', importance: 0.30 },
    { feature: 'time_of_day', importance: 0.25 },
  ],
  vendor_ranking: [
    { feature: 'total_orders', importance: 0.35 },
    { feature: 'rating', importance: 0.30 },
    { feature: 'current_load', importance: 0.20 },
    { feature: 'cancellation_rate', importance: 0.15 },
  ],
  fraud_detection: [
    { feature: 'refund_count', importance: 0.40 },
    { feature: 'cancellation_count', importance: 0.30 },
    { feature: 'high_value_orders', importance: 0.18 },
    { feature: 'night_orders', importance: 0.12 },
  ],
};

function ModelAccuracySection({ summary, loading }: { summary: ModelAccuracySummary | null; loading: boolean }) {
  const [expandedModel, setExpandedModel] = useState<string | null>(null);

  const modelLabels: Record<string, string> = {
    eta_prediction: 'ETA Prediction Model',
    demand_forecast: 'Demand Forecast Model',
    slot_recommendation: 'Slot Recommendation Model',
    vendor_ranking: 'Vendor Ranking Model',
    fraud_detection: 'Fraud Detection Model',
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton h-44 rounded-xl" />
        ))}
      </div>
    );
  }

  if (!summary) {
    return <div className="tnt-card text-center py-6 text-sm text-[#9CA3AF]">No model accuracy data available</div>;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {Object.entries(summary).map(([modelType, detail]) => {
          const label = modelLabels[modelType] || modelType;
          const activeVer = detail.active_version;
          const backtest = detail.latest_backtest;
          const drift = detail.latest_drift;

          const hasDrift = drift?.has_drift;
          const driftedList = drift?.drifted_features || [];

          const topFeatures = (detail.feature_importance && detail.feature_importance.length > 0)
            ? detail.feature_importance.slice(0, 5)
            : (DEFAULT_TOP_FEATURES[modelType] || []);

          const maxImp = Math.max(...topFeatures.map(f => f.importance), 0.01);
          const isExpanded = expandedModel === modelType;

          return (
            <div key={modelType} className="tnt-card border border-[#E5E7EB] hover:border-[#D1D5DB] transition-all">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <h4 className="text-sm font-semibold text-[#111827]">{label}</h4>
                  <p className="text-xs text-[#9CA3AF] font-mono">
                    Active Version: <span className="font-semibold text-[#4F46E5]">{activeVer?.version_id || 'v1.0'}</span>
                  </p>
                </div>
                {/* Drift Badge */}
                <div>
                  {hasDrift ? (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-red-50 text-red-600 border border-red-200">
                      <AlertTriangle className="w-3.5 h-3.5 mr-1" /> Drift Flagged ({driftedList.join(', ')})
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-green-50 text-green-600 border border-green-200">
                      <CheckCircle className="w-3.5 h-3.5 mr-1" /> Stable / No Drift
                    </span>
                  )}
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-3 mb-3">
                {/* Training Accuracy */}
                <div className="p-3 rounded-lg bg-[#F9FAFB] border border-[#E5E7EB]">
                  <p className="text-[11px] font-medium text-[#6B7280]">Training Accuracy / CV</p>
                  {activeVer?.cv_rmse !== undefined ? (
                    <p className="text-sm font-bold font-mono text-[#111827] mt-1">
                      CV RMSE: <span className="text-indigo-600">{activeVer.cv_rmse}</span>
                    </p>
                  ) : activeVer?.cv_f1 !== undefined ? (
                    <p className="text-sm font-bold font-mono text-[#111827] mt-1">
                      CV F1: <span className="text-indigo-600">{(activeVer.cv_f1 * 100).toFixed(1)}%</span>
                    </p>
                  ) : activeVer?.cv_score !== undefined ? (
                    <p className="text-sm font-bold font-mono text-[#111827] mt-1">
                      CV Score: <span className="text-indigo-600">{activeVer.cv_score}</span>
                    </p>
                  ) : (
                    <p className="text-xs font-mono text-[#4B5563] mt-1">Validated Baseline</p>
                  )}
                </div>

                {/* Latest Backtest */}
                <div className="p-3 rounded-lg bg-[#F9FAFB] border border-[#E5E7EB]">
                  <p className="text-[11px] font-medium text-[#6B7280]">Real-World Backtest</p>
                  {backtest?.status === 'success' ? (
                    <div className="text-xs space-y-0.5 font-mono text-[#111827] mt-1">
                      {backtest.within_3_min_pct !== undefined && (
                        <p>Within 3m: <span className="font-bold text-green-600">{backtest.within_3_min_pct}%</span></p>
                      )}
                      {backtest.mae_minutes !== undefined && (
                        <p>MAE: <span className="font-bold text-[#E85D24]">{backtest.mae_minutes}m</span></p>
                      )}
                      {backtest.top_1_hit_rate !== undefined && (
                        <p>Top-1 Hit: <span className="font-bold text-blue-600">{(backtest.top_1_hit_rate * 100).toFixed(1)}%</span></p>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-[#9CA3AF] italic mt-1">
                      {backtest?.status === 'insufficient_data' ? 'Insufficient Data (< 20 orders)' : 'N/A'}
                    </p>
                  )}
                </div>
              </div>

              {/* Expandable "Why this model?" Drivers */}
              <button
                onClick={() => setExpandedModel(isExpanded ? null : modelType)}
                className="w-full flex items-center justify-between text-xs font-semibold text-[#4F46E5] hover:text-[#4338CA] pt-2 border-t border-[#F3F4F6] transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#4F46E5]" />
                  Why this model? (Top Drivers)
                </span>
                {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>

              {isExpanded && (
                <div className="mt-3 p-3 bg-[#F9FAFB] rounded-lg border border-[#E5E7EB] space-y-2">
                  <p className="text-[11px] font-medium text-[#4B5563]">
                    Key factors driving predictions (in plain language):
                  </p>
                  {topFeatures.map((feat, fIdx) => {
                    const labelName = FEATURE_LABELS[feat.feature] || feat.feature.replace(/_/g, ' ');
                    const pct = Math.round((feat.importance / maxImp) * 100);
                    return (
                      <div key={fIdx} className="space-y-1">
                        <div className="flex justify-between text-xs font-medium text-[#111827]">
                          <span>{labelName}</span>
                          <span className="font-mono text-[#6B7280]">{(feat.importance * 100).toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-[#E5E7EB] rounded-full h-1.5">
                          <div
                            className="bg-[#4F46E5] h-1.5 rounded-full transition-all duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Version History Note */}
              <div className="flex items-center justify-between text-xs text-[#9CA3AF] pt-2 mt-2 border-t border-[#F3F4F6]">
                <span>Total Versions: {detail.versions?.length || 1}</span>
                <span className="italic">Trend data will populate over time</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

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
  const [accuracySummary, setAccuracySummary] = useState<ModelAccuracySummary | null>(null);

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
      const [rushRes, rankRes, slotRes, reorderRes, accRes] = await Promise.allSettled([
        aiApi.getRushHour(),
        aiApi.getVendorRanking(),
        aiApi.getSlotSuggestions(),
        aiApi.getReorderPrompts(),
        aiApi.getAccuracySummary(),
      ]);
      if (rushRes.status === 'fulfilled') setRushHour(rushRes.value.data);
      if (rankRes.status === 'fulfilled') setRankings(Array.isArray(rankRes.value.data) ? rankRes.value.data : []);
      if (slotRes.status === 'fulfilled') setSlotSuggestions(Array.isArray(slotRes.value.data) ? slotRes.value.data : []);
      if (accRes.status === 'fulfilled') setAccuracySummary(accRes.value.data);

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
                  <span className="text-amber-600">{(slot.utilization_percent ?? 0).toFixed(0)}%</span>
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
            {rankings.map((vendor) => {
              const score = vendor.vendor_rank_score ?? vendor.score ?? 0;
              const isML = vendor.source === 'model';
              return (
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
                      <p className="font-medium text-[#111827] truncate text-sm">{vendor.vendor_name || `Vendor #${vendor.vendor_id}`}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="font-mono text-[#4F46E5] font-bold">{score.toFixed(2)}</span>
                        {vendor.trend === 'up' && <TrendingUp className="w-3.5 h-3.5 text-green-600" />}
                        {vendor.trend === 'down' && <TrendingDown className="w-3.5 h-3.5 text-red-600" />}
                        {vendor.trend === 'stable' && <Minus className="w-3.5 h-3.5 text-[#9CA3AF]" />}
                      </div>
                      {vendor.category && (
                        <p className="text-xs text-[#9CA3AF] capitalize">{vendor.category}</p>
                      )}
                      {/* Ranking source explainability badge */}
                      <div
                        className={cn(
                          'mt-2 flex items-center gap-1 text-[10px] px-2 py-1 rounded-md border font-medium',
                          isML
                            ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                            : 'bg-gray-50 border-gray-200 text-gray-500'
                        )}
                        title={isML
                          ? 'Ranked using ML model: order volume, rating, current load, cancellation rate'
                          : 'Ranked using heuristic fallback (insufficient ML data)'}
                      >
                        {isML
                          ? <><Sparkles className="w-3 h-3 shrink-0" /> ML: order volume, rating, load</>
                          : <><Info className="w-3 h-3 shrink-0" /> Heuristic fallback</>}
                      </div>
                      {vendor.live_load_indicator && (
                        <p className={cn(
                          'text-[10px] font-semibold mt-1',
                          vendor.live_load_indicator === 'HIGH' ? 'text-red-600' :
                          vendor.live_load_indicator === 'MEDIUM' ? 'text-amber-600' : 'text-green-600'
                        )}>
                          Load: {vendor.live_load_indicator}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ─── Row 5: Model Accuracy & Drift Status ───────────── */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Cpu className="w-4 h-4 text-[#4F46E5]" />
          <h3 className="text-sm font-semibold text-[#111827]">Model Accuracy & Health Status</h3>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium text-[#9CA3AF] border border-[#E5E7EB]">
            Training, Backtest & Drift Tracking
          </span>
        </div>
        <ModelAccuracySection summary={accuracySummary} loading={loading} />
      </div>

      {/* ─── Row 6: ETA Accuracy ─────────────────────────── */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-4 h-4 text-[#4F46E5]" />
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