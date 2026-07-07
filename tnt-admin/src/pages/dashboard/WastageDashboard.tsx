import React, { useEffect, useState } from 'react';
import {
  IndianRupee,
  AlertTriangle,
  TrendingDown,
  Trash2,
  RefreshCw
} from 'lucide-react';
import toast from 'react-hot-toast';
import { StatCard } from '../../components/ui/StatCard';
import { adminApi } from '../../api/admin';
import { formatPaise, formatNumber } from '../../utils/format';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';

export default function WastageDashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchWastage = async () => {
    try {
      const res = await adminApi.getWastageAnalytics();
      setData(res.data);
    } catch (err: any) {
      toast.error('Failed to load wastage analytics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchWastage();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchWastage();
  };

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  const {
    cancelled_orders = 0,
    cancellation_rate = 0,
    wasted_revenue = 0,
    daily_waste_average = 0,
    wasted_items = [],
    vendor_waste = [],
    daily_trend = []
  } = data || {};

  // Map data for charts
  const trendData = daily_trend.map((t: any) => ({
    label: t.date ? t.date.split('-').slice(1).join('/') : '', // MM/DD
    revenue: (t.wasted_revenue || 0) / 100, // INR
    count: t.cancelled_count || 0
  }));

  const vendorData = vendor_waste.map((v: any) => ({
    name: v.vendor_name || 'Unknown',
    revenue: (v.wasted_revenue || 0) / 100,
    count: v.cancelled_count || 0
  }));

  return (
    <div className="space-y-6 text-[#F1F0FF]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-[#F1F0FF] tracking-tight">Food Wastage Dashboard</h1>
          <p className="text-sm text-[#9B9BC4]">Monitor and track university-wide food waste reduction metrics from cancelled orders.</p>
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-[#F1F0FF] bg-[#1A1A2E] border border-[#2D2D44] rounded-lg hover:bg-[#252538] transition-colors shadow-sm"
          disabled={refreshing}
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Wasted Revenue"
          value={formatPaise(wasted_revenue)}
          icon={IndianRupee}
          color="red"
          description="Value of food cancelled after prep"
        />
        <StatCard
          title="Cancelled Orders"
          value={formatNumber(cancelled_orders)}
          icon={AlertTriangle}
          color="amber"
          description="Total orders cancelled (last 90 days)"
        />
        <StatCard
          title="Cancellation Waste Rate"
          value={`${cancellation_rate}%`}
          icon={TrendingDown}
          color="indigo"
          description="Percentage of wasted orders"
        />
        <StatCard
          title="Daily Waste Avg"
          value={formatPaise(daily_waste_average * 100)} // convert INR to paise for format
          icon={Trash2}
          color="rose"
          description="Wasted revenue average per day"
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trend Area Chart */}
        <div className="tnt-card">
          <h3 className="text-base font-bold text-[#F1F0FF] mb-4 tracking-tight">Wasted Revenue Trend (Last 30 Days)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorWaste" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EF4444" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2D2D44" />
                <XAxis dataKey="label" tick={{ fill: '#9B9BC4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#9B9BC4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#1A1A2E', borderColor: '#2D2D44', color: '#F1F0FF' }} />
                <Legend />
                <Area type="monotone" dataKey="revenue" name="Wasted Revenue (₹)" stroke="#EF4444" fillOpacity={1} fill="url(#colorWaste)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Vendor Waste Bar Chart */}
        <div className="tnt-card">
          <h3 className="text-base font-bold text-[#F1F0FF] mb-4 tracking-tight">Wastage by Vendor</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={vendorData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2D2D44" />
                <XAxis dataKey="name" tick={{ fill: '#9B9BC4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#9B9BC4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#1A1A2E', borderColor: '#2D2D44', color: '#F1F0FF' }} />
                <Legend />
                <Bar dataKey="revenue" name="Wasted Revenue (₹)" fill="#F59E0B" radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Wasted Items & Detailed Vendors List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Wasted Items */}
        <div className="tnt-card">
          <h3 className="text-base font-bold text-[#F1F0FF] mb-4 tracking-tight">Top 5 Wasted Menu Items</h3>
          <div className="divide-y divide-[#2D2D44]">
            {wasted_items.length === 0 ? (
              <div className="py-8 text-center text-sm text-[#9B9BC4]">No items registered waste.</div>
            ) : (
              wasted_items.map((item: any, idx: number) => (
                <div key={idx} className="py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-red-950 text-red-400 text-xs font-bold flex items-center justify-center">
                      {idx + 1}
                    </span>
                    <span className="font-semibold text-[#F1F0FF] text-sm">{item.name}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold text-[#F1F0FF]">{formatPaise(item.wasted_value)}</div>
                    <div className="text-xs text-[#9B9BC4]">{item.cancelled_count} cancellations</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Detailed Vendor list */}
        <div className="tnt-card">
          <h3 className="text-base font-bold text-[#F1F0FF] mb-4 tracking-tight">Vendor Waste Leaderboard</h3>
          <div className="divide-y divide-[#2D2D44]">
            {vendor_waste.length === 0 ? (
              <div className="py-8 text-center text-sm text-[#9B9BC4]">No vendors registered waste.</div>
            ) : (
              vendor_waste.map((v: any, idx: number) => (
                <div key={idx} className="py-3 flex items-center justify-between">
                  <span className="font-semibold text-[#F1F0FF] text-sm">{v.vendor_name}</span>
                  <div className="text-right">
                    <div className="text-sm font-bold text-red-400">{formatPaise(v.wasted_revenue)}</div>
                    <div className="text-xs text-[#9B9BC4]">{v.cancelled_count} orders cancelled</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
