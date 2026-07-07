import React, { useCallback, useEffect, useState } from 'react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Line, LineChart } from 'recharts';
import { RefreshCw, RefreshCcw, ShieldAlert, MessageSquareWarning, Printer as PrinterIcon, Droplet } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import { formatShortDate, formatRupees } from '../../utils/format';
import { chartTokens } from '../../components/charts/shared/chartTheme';
import { TNTTooltip } from '../../components/charts/shared/tntTooltip';
import '../../components/charts/shared/tntTooltip.css';

interface TrendPoint { date: string; count: number; amount?: number; }
interface PrinterUsage {
  total_printers: number; total_queue: number; total_capacity_pages_per_hour: number;
  avg_ink_level_pct: number; low_paper_printers: number; by_status: Record<string, number>;
  per_printer: { id: number; name: string; queue_depth: number; ink_level_pct: number; paper_count: number }[];
}
interface TrendsResponse {
  days: number;
  refund_trend: TrendPoint[];
  fraud_trend: TrendPoint[];
  complaint_trend: TrendPoint[];
  printer_usage: PrinterUsage;
  totals: { refunds: number; refund_amount: number; fraud_flags: number; complaints: number };
}

function TrendChart({ data, color, label }: { data: TrendPoint[]; color: string; label: string }) {
  const formatted = data.map(d => ({ ...d, label: formatShortDate(d.date) }));
  return (
    <div className="tnt-card h-full">
      <h3 className="text-sm font-semibold text-[#374151] mb-3">{label}</h3>
      {formatted.length === 0 ? (
        <div className="h-[160px] flex items-center justify-center text-sm text-[#9CA3AF]">No data in range</div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={formatted} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray={chartTokens.grid.dasharray} stroke={chartTokens.grid.stroke} strokeOpacity={chartTokens.grid.strokeOpacity} />
            <XAxis dataKey="label" tick={{ fill: chartTokens.text.axis, fontSize: 11 }} axisLine={{ stroke: chartTokens.grid.stroke, strokeOpacity: 0.3 }} tickLine={false} />
            <YAxis tick={{ fill: chartTokens.text.axis, fontSize: 11 }} axisLine={{ stroke: chartTokens.grid.stroke, strokeOpacity: 0.3 }} tickLine={false} allowDecimals={false} />
            <Tooltip content={<TNTTooltip />} />
            <Line type="monotone" dataKey="count" stroke={color} strokeWidth={2} dot={{ r: 2 }} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default function AnalyticsTrends() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<TrendsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getAnalyticsTrends(days);
      setData(res.data);
    } catch { toast.error('Failed to load trends'); }
    finally { setLoading(false); }
  }, [days]);
  useEffect(() => { load(); }, [load]);

  const pu = data?.printer_usage;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-[#111827]">Analytics Trends</h2>
          <p className="text-sm text-[#6B7280] mt-1">Refunds, fraud, complaints & printer usage over time</p>
        </div>
        <div className="flex items-center gap-2">
          <select aria-label="Time range" className="tnt-select w-36" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={60}>Last 60 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button onClick={load} className="btn-ghost" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
        </div>
      </div>

      {loading || !data ? (
        <div className="skeleton h-96 rounded-xl" />
      ) : (
        <>
          {/* Summary tiles */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="tnt-card">
              <div className="flex items-center gap-2 mb-1"><RefreshCcw className="w-4 h-4 text-red-500" /><span className="text-xs text-[#6B7280]">Refunds</span></div>
              <p className="text-2xl font-bold font-mono text-[#111827]">{data.totals.refunds}</p>
              <p className="text-xs text-[#9CA3AF]">{formatRupees(data.totals.refund_amount)}</p>
            </div>
            <div className="tnt-card">
              <div className="flex items-center gap-2 mb-1"><ShieldAlert className="w-4 h-4 text-amber-500" /><span className="text-xs text-[#6B7280]">Fraud Flags</span></div>
              <p className="text-2xl font-bold font-mono text-[#111827]">{data.totals.fraud_flags}</p>
            </div>
            <div className="tnt-card">
              <div className="flex items-center gap-2 mb-1"><MessageSquareWarning className="w-4 h-4 text-purple-500" /><span className="text-xs text-[#6B7280]">Complaints</span></div>
              <p className="text-2xl font-bold font-mono text-[#111827]">{data.totals.complaints}</p>
            </div>
            <div className="tnt-card">
              <div className="flex items-center gap-2 mb-1"><PrinterIcon className="w-4 h-4 text-[#E85D24]" /><span className="text-xs text-[#6B7280]">Printer Queue</span></div>
              <p className="text-2xl font-bold font-mono text-[#111827]">{pu?.total_queue ?? 0}</p>
              <p className="text-xs text-[#9CA3AF]">{pu?.total_printers ?? 0} printers</p>
            </div>
          </div>

          {/* Trend charts */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <TrendChart data={data.refund_trend} color={chartTokens.brand.red} label="Refund Trend" />
            <TrendChart data={data.fraud_trend} color={chartTokens.brand.amber} label="Fraud Trend" />
            <TrendChart data={data.complaint_trend} color={chartTokens.brand.indigo} label="Complaint Trend" />
          </div>

          {/* Printer usage */}
          {pu && (
            <div className="tnt-card">
              <div className="flex items-center gap-2 mb-4">
                <Droplet className="w-5 h-5 text-blue-500" />
                <h3 className="font-semibold text-[#111827]">Printer Usage</h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-4">
                <div><p className="text-xs text-[#6B7280]">Avg Ink</p><p className="font-mono font-semibold">{pu.avg_ink_level_pct}%</p></div>
                <div><p className="text-xs text-[#6B7280]">Low Paper</p><p className="font-mono font-semibold">{pu.low_paper_printers}</p></div>
                <div><p className="text-xs text-[#6B7280]">Total Capacity/hr</p><p className="font-mono font-semibold">{pu.total_capacity_pages_per_hour}</p></div>
                {Object.entries(pu.by_status).map(([s, c]) => (
                  <div key={s}><p className="text-xs text-[#6B7280] capitalize">{s}</p><p className="font-mono font-semibold">{c}</p></div>
                ))}
              </div>
              {pu.per_printer.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-[#6B7280] border-b border-[#E5E7EB]">
                        <th className="py-2 px-3">Printer</th><th className="py-2 px-3">Queue</th><th className="py-2 px-3">Ink</th><th className="py-2 px-3">Paper</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pu.per_printer.map(p => (
                        <tr key={p.id} className="border-b border-[#F3F4F6]">
                          <td className="py-2 px-3 font-medium text-[#111827]">{p.name}</td>
                          <td className="py-2 px-3 font-mono">{p.queue_depth}</td>
                          <td className="py-2 px-3 font-mono">{p.ink_level_pct}%</td>
                          <td className="py-2 px-3 font-mono">{p.paper_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
