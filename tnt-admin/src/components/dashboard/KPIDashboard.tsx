import React, { useEffect, useState } from 'react';
import {
  Users, Store, ShoppingBag, IndianRupee, Clock, Activity,
  Calendar, Briefcase, Download, AlertCircle, RefreshCw,
  TrendingUp, Award, HelpCircle, FileText, CheckCircle
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

      const res = await adminApi.exportKPIs(params);
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
        {/* Trend Area Chart */}
        <div className="tnt-card lg:col-span-2">
          <h3 className="text-base font-bold text-[#111827] mb-1">Order Volume Aggregations</h3>
          <p className="text-xs text-[#9CA3AF] mb-4">Historical daily trends in order counts within date window</p>
          <div className="h-[250px] w-full">
            {orderTrendData.length > 0 ? (
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
                  <Tooltip
                    contentStyle={{
                      background: '#ffffff',
                      border: '1px solid #E5E7EB',
                      borderRadius: '12px',
                      fontSize: '12px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="Orders"
                    stroke="#4F46E5"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#kpiTrend)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF]">
                No trend data available for selected filters.
              </div>
            )}
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
                <th className="py-2.5 px-4">Vendor Name</th>
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
                      {index + 1}. {vp.vendor_name}
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
