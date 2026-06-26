import React, { useEffect, useState } from 'react';
import {
  Users, Store, ShoppingBag, IndianRupee, Clock, Activity,
  Calendar, Briefcase, Download, AlertCircle, RefreshCw,
  TrendingUp, Award, HelpCircle, FileText, CheckCircle, Brain
} from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import type { KPIData, Vendor } from '../../types';
import { StatCard } from '../ui/StatCard';
import { KPIHeatmap } from '../charts/KPIHeatmap';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, BarChart, Bar, PieChart, Pie, Cell, Legend
} from 'recharts';
import { formatPaise, formatNumber } from '../../utils/format';

const DEPARTMENTS = [
  'Computer Science',
  'Electrical Engineering',
  'Mechanical Engineering',
  'Business Administration',
  'Basic Sciences',
  'Humanities',
];

const COLORS = ['#4F46E5', '#14B8A6', '#F59E0B', '#EF4444', '#10B981', '#6366F1'];

export function KPIDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [kpis, setKpis] = useState<KPIData | null>(null);
  const [vendors, setVendors] = useState<Vendor[]>([]);

  // Filter States
  const [dateFrom, setDateFrom] = useState<string>(
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [dateTo, setDateTo] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [department, setDepartment] = useState<string>('');
  const [vendorId, setVendorId] = useState<string>('');

  const [exportingExcel, setExportingExcel] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [activeChartTab, setActiveChartTab] = useState<'orders' | 'revenue' | 'departments' | 'categories' | 'peakhours' | 'slots' | 'cancellations'>('orders');

  const fetchVendors = async () => {
    try {
      const res = await adminApi.getVendors();
      setVendors(Array.isArray(res.data) ? res.data : []);
    } catch {
      // silent
    }
  };

  const fetchKPIs = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = {
        date_from: dateFrom,
        date_to: dateTo,
      };
      if (department) params.department = department;
      if (vendorId) params.vendor_id = parseInt(vendorId);

      const res = await adminApi.getKPIs(params);
      setKpis(res.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch institutional KPIs.');
      toast.error('Failed to load KPIs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVendors();
  }, []);

  useEffect(() => {
    fetchKPIs();
  }, [dateFrom, dateTo, department, vendorId]);

  const handleExport = async (format: 'excel' | 'pdf') => {
    if (format === 'excel') setExportingExcel(true);
    else setExportingPdf(true);

    try {
      const params: Record<string, any> = {
        format,
        date_from: dateFrom,
        date_to: dateTo,
      };
      if (department) params.department = department;
      if (vendorId) params.vendor_id = parseInt(vendorId);

      const res = await adminApi.exportKPIs(params as any);
      const blob = new Blob([res.data], {
        type: format === 'excel'
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          : 'application/pdf'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `tnt_kpi_report_${new Date().toISOString().slice(0,10)}.${format === 'excel' ? 'xlsx' : 'pdf'}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      toast.success(`${format.toUpperCase()} Exported successfully`);
    } catch {
      toast.error(`Failed to export report in ${format} format`);
    } finally {
      setExportingExcel(false);
      setExportingPdf(false);
    }
  };

  if (loading && !kpis) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-2">
          <RefreshCw className="w-8 h-8 text-[#4F46E5] animate-spin" />
          <p className="text-sm text-[#4B5563]">Calculating institutional analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="tnt-card p-6 border-red-200 bg-red-50/50 flex flex-col items-center text-center">
        <AlertCircle className="w-12 h-12 text-red-500 mb-2" />
        <h4 className="text-lg font-bold text-red-800">Error Loading Metrics</h4>
        <p className="text-sm text-red-600 mt-1 max-w-md">{error}</p>
        <button onClick={fetchKPIs} className="btn-primary mt-4">
          Try Again
        </button>
      </div>
    );
  }

  // Formatting variables
  const uKpis = kpis?.university_kpis;
  const opKpis = kpis?.operational_kpis;
  const bKpis = kpis?.business_kpis;
  const enKpis = kpis?.engagement_kpis;

  // Breakdown of category
  const categoryPieData = [
    { name: 'Food Orders', value: uKpis?.food_orders || 0 },
    { name: 'Stationery Orders', value: uKpis?.stationery_orders || 0 }
  ];

  // Engagement Points usage
  const pointsRedeemed = enKpis?.points_redeemed || 0;
  const vouchersRedeemed = enKpis?.vouchers_redeemed_count || 0;

  // Trend Chart Data
  const orderTrendData = (uKpis?.daily_trend || []).map(d => ({
    label: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    Orders: d.count
  }));

  const revenueTrendData = (kpis?.revenue_trends || []).map(d => ({
    label: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    'Revenue (₹)': d.revenue_inr
  }));

  const deptData = (kpis?.department_analytics || []).map(d => ({
    name: d.department,
    Orders: d.order_count,
    'Revenue (₹)': d.revenue_inr
  }));

  const foodMap = new Map((kpis?.food_trends || []).map(t => [t.date, t]));
  const statMap = new Map((kpis?.stationery_trends || []).map(t => [t.date, t]));
  const allDates = Array.from(new Set([
    ...(kpis?.food_trends || []).map(t => t.date),
    ...(kpis?.stationery_trends || []).map(t => t.date)
  ])).sort();

  const categoryTrendData = allDates.map(date => {
    const f = foodMap.get(date);
    const s = statMap.get(date);
    return {
      label: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      'Food Orders': f?.orders || 0,
      'Stationery Orders': s?.orders || 0,
      'Food Revenue (₹)': f?.revenue_inr || 0,
      'Stationery Revenue (₹)': s?.revenue_inr || 0
    };
  });

  const peakHourData = (kpis?.peak_hour_analysis || []).map(d => ({
    label: `${d.hour}:00`,
    'Food Orders': d.food_orders,
    'Stationery Orders': d.stationery_orders
  }));

  const slotUsageData = (kpis?.slot_usage_analysis || []).map(d => ({
    label: `${d.hour}:00`,
    'Booked Slots': d.booked_orders,
    'Total Capacity': d.total_capacity,
    'Utilization %': d.utilization_pct
  }));

  const cancellationTrendData = (kpis?.cancellation_trends || []).map(d => ({
    label: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    'Cancellation Rate (%)': d.cancellation_rate,
    'Cancelled Count': d.cancelled_count
  }));

  return (
    <div className="space-y-6">
      {/* Filters Panel */}
      <div className="tnt-card p-4 flex flex-wrap gap-4 items-center justify-between bg-white border border-[#E5E7EB] shadow-sm rounded-xl">
        <div className="flex flex-wrap gap-4 items-center flex-1">
          {/* Start Date */}
          <div className="flex flex-col gap-1 min-w-[140px]">
            <label className="text-[10px] font-bold uppercase tracking-wider text-[#4B5563]">Start Date</label>
            <div className="relative">
              <Calendar className="absolute left-3 top-2.5 w-4 h-4 text-[#9CA3AF]" />
              <input
                type="date"
                value={dateFrom}
                onChange={e => setDateFrom(e.target.value)}
                className="pl-9 pr-3 py-1.5 w-full border border-[#E5E7EB] rounded-lg text-sm font-medium text-[#111827] focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
              />
            </div>
          </div>

          {/* End Date */}
          <div className="flex flex-col gap-1 min-w-[140px]">
            <label className="text-[10px] font-bold uppercase tracking-wider text-[#4B5563]">End Date</label>
            <div className="relative">
              <Calendar className="absolute left-3 top-2.5 w-4 h-4 text-[#9CA3AF]" />
              <input
                type="date"
                value={dateTo}
                onChange={e => setDateTo(e.target.value)}
                className="pl-9 pr-3 py-1.5 w-full border border-[#E5E7EB] rounded-lg text-sm font-medium text-[#111827] focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
              />
            </div>
          </div>

          {/* Department Filter */}
          <div className="flex flex-col gap-1 min-w-[180px]">
            <label className="text-[10px] font-bold uppercase tracking-wider text-[#4B5563]">Department</label>
            <div className="relative">
              <Briefcase className="absolute left-3 top-2.5 w-4 h-4 text-[#9CA3AF]" />
              <select
                value={department}
                onChange={e => setDepartment(e.target.value)}
                className="pl-9 pr-3 py-1.5 w-full border border-[#E5E7EB] rounded-lg text-sm font-medium text-[#111827] bg-white focus:outline-none focus:ring-1 focus:ring-[#4F46E5] appearance-none"
              >
                <option value="">All Departments</option>
                {DEPARTMENTS.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Vendor Filter */}
          <div className="flex flex-col gap-1 min-w-[180px]">
            <label className="text-[10px] font-bold uppercase tracking-wider text-[#4B5563]">Vendor</label>
            <div className="relative">
              <Store className="absolute left-3 top-2.5 w-4 h-4 text-[#9CA3AF]" />
              <select
                value={vendorId}
                onChange={e => setVendorId(e.target.value)}
                className="pl-9 pr-3 py-1.5 w-full border border-[#E5E7EB] rounded-lg text-sm font-medium text-[#111827] bg-white focus:outline-none focus:ring-1 focus:ring-[#4F46E5] appearance-none"
              >
                <option value="">All Vendors</option>
                {vendors.map(v => (
                  <option key={v.id} value={v.id}>{v.name || `Vendor #${v.id}`}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 mt-4 sm:mt-0">
          <button
            onClick={() => handleExport('excel')}
            disabled={exportingExcel}
            className="btn-secondary text-xs"
          >
            {exportingExcel ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            Export Excel
          </button>
          <button
            onClick={() => handleExport('pdf')}
            disabled={exportingPdf}
            className="btn-primary text-xs"
          >
            {exportingPdf ? (
              <RefreshCw className="w-4 h-4 animate-spin animate-reverse" />
            ) : (
              <FileText className="w-4 h-4" />
            )}
            Export PDF
          </button>
        </div>
      </div>

      {/* AI Insights Panel */}
      {kpis?.ai_insights && kpis.ai_insights.length > 0 && (
        <div className="tnt-card p-5 border border-indigo-100 bg-gradient-to-r from-indigo-50/50 via-white to-purple-50/50 shadow-sm rounded-xl">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-5 h-5 text-indigo-600 animate-pulse" />
            <h3 className="text-base font-bold text-[#111827]">AI-Powered Heuristic Insights</h3>
            <span className="text-[10px] uppercase font-bold text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-100">Live Diagnostics</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {kpis.ai_insights.map((insight, idx) => {
              const getInsightColors = (type: string) => {
                if (type === 'success') return { bg: 'bg-emerald-50 border-emerald-100', text: 'text-emerald-800', badge: 'bg-emerald-500/10 text-emerald-700', border: 'border-emerald-200' };
                if (type === 'warning') return { bg: 'bg-amber-50 border-amber-100', text: 'text-amber-800', badge: 'bg-amber-500/10 text-amber-700', border: 'border-amber-200' };
                if (type === 'danger') return { bg: 'bg-rose-50 border-rose-100', text: 'text-rose-800', badge: 'bg-rose-500/10 text-rose-700', border: 'border-rose-200' };
                return { bg: 'bg-blue-50 border-blue-100', text: 'text-blue-800', badge: 'bg-blue-500/10 text-blue-700', border: 'border-blue-200' };
              };
              const colors = getInsightColors(insight.type);
              return (
                <div key={idx} className={`p-4 border rounded-xl shadow-xs ${colors.bg} ${colors.border}`}>
                  <div className="flex items-start gap-2.5">
                    <div className="flex flex-col gap-1 flex-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${colors.badge} uppercase`}>
                          {insight.type}
                        </span>
                        <h4 className={`text-sm font-bold ${colors.text}`}>{insight.title}</h4>
                      </div>
                      <p className="text-xs text-[#4B5563] mt-1.5 leading-relaxed">{insight.detail}</p>
                      <div className="mt-2.5 pt-2 border-t border-dashed border-[#E5E7EB] text-xs text-[#1F2937]">
                        <span className="font-semibold text-indigo-700">Recommendation: </span>
                        {insight.recommendation}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* KPI Cards Sections */}
      <div className="space-y-6">
        {/* University & Operational KPIs */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-[#9CA3AF] mb-3">University & Operations</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Total Orders"
              value={uKpis?.total_orders || 0}
              subtitle={`${uKpis?.food_orders || 0} Food / ${uKpis?.stationery_orders || 0} Stationery`}
              icon={ShoppingBag}
              accent="indigo"
            />
            <StatCard
              title="Avg Waiting Time"
              value={`${opKpis?.avg_waiting_time_minutes || 0}m`}
              subtitle="Prep to completed duration"
              icon={Clock}
              accent="blue"
            />
            <StatCard
              title="Queue Reduction Rate"
              value={`${opKpis?.queue_reduction_pct || 100}%`}
              subtitle="Orders processed successfully"
              icon={CheckCircle}
              accent="green"
            />
            <StatCard
              title="Slot Utilization"
              value={`${opKpis?.slot_utilization_pct || 0}%`}
              subtitle="Active slot bookings filled"
              icon={Activity}
              accent="amber"
            />
          </div>
        </div>

        {/* Business & Engagement KPIs */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-[#9CA3AF] mb-3">Financials & Engagement</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Total Revenue"
              value={`₹${(bKpis?.revenue_inr || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
              subtitle={`Refunded: ₹${(bKpis?.refunds_inr || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
              icon={IndianRupee}
              accent="green"
            />
            <StatCard
              title="Active System Users"
              value={enKpis?.active_users || 0}
              subtitle={`${enKpis?.returning_users || 0} returning (>= 2 orders)`}
              icon={Users}
              accent="indigo"
            />
            <StatCard
              title="Cancellation Rate"
              value={`${bKpis?.cancellation_rate_pct || 0}%`}
              subtitle="Cancelled orders share"
              icon={AlertCircle}
              accent="red"
            />
            <StatCard
              title="Rewards Redeemed"
              value={vouchersRedeemed}
              subtitle={`${pointsRedeemed.toFixed(0)} Points redeemed`}
              icon={Award}
              accent="amber"
            />
          </div>
        </div>
      </div>

      {/* Main Aggregations Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Extended Trend Chart Tabs */}
        <div className="tnt-card lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex flex-wrap gap-2 justify-between items-center mb-4">
              <div>
                <h3 className="text-base font-bold text-[#111827]">Institutional KPI Visualizations</h3>
                <p className="text-xs text-[#9CA3AF] mt-0.5">Explore trend breakdowns, categories, peak loads, and cancellations</p>
              </div>
            </div>

            {/* Tabs Headers */}
            <div className="flex flex-wrap gap-1 border-b border-[#E5E7EB] pb-px mb-4">
              {[
                { id: 'orders', label: 'Orders' },
                { id: 'revenue', label: 'Revenue' },
                { id: 'departments', label: 'Departments' },
                { id: 'categories', label: 'Food vs Stationery' },
                { id: 'peakhours', label: 'Peak Hour Load' },
                { id: 'slots', label: 'Slots Capacity' },
                { id: 'cancellations', label: 'Cancellations' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveChartTab(tab.id as any)}
                  className={`pb-2 px-3 text-xs font-semibold border-b-2 -mb-px transition-all duration-200 ${
                    activeChartTab === tab.id
                      ? 'border-[#4F46E5] text-[#4F46E5]'
                      : 'border-transparent text-[#6B7280] hover:text-[#374151]'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Active Chart Render */}
            <div className="h-[260px] w-full mt-2">
              {activeChartTab === 'orders' && (
                orderTrendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={orderTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="kpiTrend" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.25} />
                          <stop offset="95%" stopColor="#4F46E5" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                      <XAxis dataKey="label" tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <YAxis tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #E5E7EB', borderRadius: '12px', fontSize: '12px' }} />
                      <Area type="monotone" dataKey="Orders" stroke="#4F46E5" strokeWidth={2.5} fillOpacity={1} fill="url(#kpiTrend)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF]">
                    No order trend data available.
                  </div>
                )
              )}

              {activeChartTab === 'revenue' && (
                revenueTrendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={revenueTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="kpiRevenue" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                          <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                      <XAxis dataKey="label" tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <YAxis tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #E5E7EB', borderRadius: '12px', fontSize: '12px' }} />
                      <Area type="monotone" dataKey="Revenue (₹)" stroke="#10B981" strokeWidth={2.5} fillOpacity={1} fill="url(#kpiRevenue)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF]">
                    No revenue trend data available.
                  </div>
                )
              )}

              {activeChartTab === 'departments' && (
                deptData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={deptData} layout="vertical" margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                      <XAxis type="number" tick={{ fill: '#9CA3AF', fontSize: 10 }} />
                      <YAxis dataKey="name" type="category" width={100} tick={{ fill: '#4B5563', fontSize: 10 }} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #E5E7EB', borderRadius: '12px', fontSize: '12px' }} />
                      <Legend />
                      <Bar name="Orders Count" dataKey="Orders" fill="#4F46E5" radius={[0, 4, 4, 0]} />
                      <Bar name="Revenue (₹)" dataKey="Revenue (₹)" fill="#14B8A6" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF]">
                    No department analytics data available.
                  </div>
                )
              )}

              {activeChartTab === 'categories' && (
                categoryTrendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={categoryTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="foodGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#4F46E5" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="statGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#F59E0B" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                      <XAxis dataKey="label" tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <YAxis tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #E5E7EB', borderRadius: '12px', fontSize: '12px' }} />
                      <Legend />
                      <Area type="monotone" name="Food Orders" dataKey="Food Orders" stroke="#4F46E5" strokeWidth={2} fill="url(#foodGrad)" />
                      <Area type="monotone" name="Stationery Orders" dataKey="Stationery Orders" stroke="#F59E0B" strokeWidth={2} fill="url(#statGrad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF]">
                    No food vs stationery category data available.
                  </div>
                )
              )}

              {activeChartTab === 'peakhours' && (
                peakHourData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={peakHourData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                      <XAxis dataKey="label" tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <YAxis tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #E5E7EB', borderRadius: '12px', fontSize: '12px' }} />
                      <Legend />
                      <Bar dataKey="Food Orders" stackId="a" fill="#4F46E5" />
                      <Bar dataKey="Stationery Orders" stackId="a" fill="#F59E0B" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF]">
                    No peak hour analysis data available.
                  </div>
                )
              )}

              {activeChartTab === 'slots' && (
                slotUsageData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={slotUsageData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                      <XAxis dataKey="label" tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <YAxis yAxisId="left" tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fill: '#F59E0B', fontSize: 10 }} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #E5E7EB', borderRadius: '12px', fontSize: '12px' }} />
                      <Legend />
                      <Area yAxisId="left" type="monotone" name="Booked Slots" dataKey="Booked Slots" stroke="#4F46E5" strokeWidth={2} fill="#4F46E5" fillOpacity={0.05} />
                      <Area yAxisId="left" type="monotone" name="Total Capacity" dataKey="Total Capacity" stroke="#9CA3AF" strokeWidth={1} strokeDasharray="4 4" fill="none" />
                      <Area yAxisId="right" type="monotone" name="Utilization %" dataKey="Utilization %" stroke="#F59E0B" strokeWidth={2.5} fill="none" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF]">
                    No slot usage data available.
                  </div>
                )
              )}

              {activeChartTab === 'cancellations' && (
                cancellationTrendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={cancellationTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="cancGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#EF4444" stopOpacity={0.25} />
                          <stop offset="95%" stopColor="#EF4444" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                      <XAxis dataKey="label" tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <YAxis tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #E5E7EB', borderRadius: '12px', fontSize: '12px' }} />
                      <Area type="monotone" name="Cancellation Rate (%)" dataKey="Cancellation Rate (%)" stroke="#EF4444" strokeWidth={2.5} fill="url(#cancGrad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF]">
                    No cancellation trend data available.
                  </div>
                )
              )}
            </div>
          </div>
        </div>

        {/* Category Share Pie Chart */}
        <div className="tnt-card">
          <h3 className="text-base font-bold text-[#111827] mb-1">University Categories</h3>
          <p className="text-xs text-[#9CA3AF] mb-4">Breakdown share of Food vs Stationery bookings</p>
          <div className="h-[250px] flex flex-col justify-center items-center">
            {categoryPieData.some(d => d.value > 0) ? (
              <>
                <ResponsiveContainer width="100%" height="70%">
                  <PieChart>
                    <Pie
                      data={categoryPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {categoryPieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex justify-center gap-6 mt-3 text-xs">
                  {categoryPieData.map((d, i) => (
                    <div key={d.name} className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-full" style={{ background: COLORS[i] }} />
                      <span className="font-medium text-[#4B5563]">{d.name} ({d.value})</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF]">
                No booking share data available.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Heatmap Grid Row */}
      {enKpis?.heatmap_grid && (
        <KPIHeatmap data={enKpis.heatmap_grid} title="Rush Intensity by Weekday & Hour" />
      )}

      {/* Vendor performance rankings */}
      <div className="tnt-card">
        <div className="mb-4">
          <h3 className="text-base font-bold text-[#111827]">Vendor Analytics Performance Rankings</h3>
          <p className="text-xs text-[#9CA3AF] mt-0.5">Aggregate efficiency and ratings sorted by order counts</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[#E5E7EB] text-[#4B5563] font-bold">
                <th className="py-2.5 px-4">Vendor Name (Ranked)</th>
                <th className="py-2.5 px-4 text-right">Orders Count</th>
                <th className="py-2.5 px-4 text-right">Completion Rate</th>
                <th className="py-2.5 px-4 text-right">Avg Prep Time</th>
                <th className="py-2.5 px-4 text-right">Average Rating</th>
              </tr>
            </thead>
            <tbody>
              {opKpis?.vendor_performance && opKpis.vendor_performance.length > 0 ? (
                opKpis.vendor_performance.map((vp, index) => (
                  <tr
                    key={vp.vendor_id}
                    className="border-b border-[#F3F4F6] text-[#374151] hover:bg-[#F9FAFB] transition-colors"
                  >
                    <td className="py-3 px-4 font-semibold text-[#111827]">
                      <div className="flex items-center gap-2">
                        <span>{index + 1}. {vp.vendor_name}</span>
                        {vp.score !== undefined && (
                          <span className="text-[10px] bg-indigo-50 text-[#4F46E5] font-bold px-1.5 py-0.5 rounded-full border border-indigo-100">
                            Score: {vp.score}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right font-mono">{vp.orders_count}</td>
                    <td className="py-3 px-4 text-right">{vp.completion_rate}%</td>
                    <td className="py-3 px-4 text-right font-mono">{vp.avg_wait_minutes} mins</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1 font-semibold text-amber-600">
                        <span>★</span>
                        <span>{vp.rating.toFixed(1)}</span>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-[#9CA3AF]">
                    No vendor performance metrics match active filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
