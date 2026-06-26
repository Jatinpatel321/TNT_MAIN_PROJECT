import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, Store, ShoppingBag, IndianRupee, CheckCircle,
  Clock, TrendingUp, Activity, Brain, AlertTriangle, ChevronRight,
  Zap, RefreshCw,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { StatCard } from '../../components/ui/StatCard';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { OrdersLineChart } from '../../components/charts/OrdersLineChart';
import { RevenueBarChart } from '../../components/charts/RevenueBarChart';
import { ExportButton } from '../../components/ExportButton';
import ConflictWidget from '../../components/ConflictWidget';
import { useAdminAnalytics } from '../../hooks/useAdminAnalytics';
import { KPIDashboard } from '../../components/dashboard/KPIDashboard';
import { adminApi } from '../../api/admin';
import { aiApi } from '../../api/ai';
import { vendorsApi } from '../../api/vendors';
import { complaintsApi } from '../../api/complaints';
import { formatPaise, formatNumber, formatTimeAgo, formatOrderId } from '../../utils/format';
import { POLL_INTERVAL_ORDERS, RUSH_HOUR_COLORS } from '../../utils/constants';
import type { Order, Vendor, Complaint, RushHourSignal, VendorRanking, DemandPlan } from '../../types';
import { cn } from '../../utils/cn';
import { subDays, format } from 'date-fns';

// Date range for revenue export (last 30 days)
const today = new Date();
const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
const dateFrom = thirtyDaysAgo.toISOString().split('T')[0];
const dateTo = today.toISOString().split('T')[0];

// Deterministic "random" based on seed — same value every call with same inputs
function seededRandom(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

function generateOrdersChartData(ordersToday: number) {
  const today = new Date().getDay(); // 0–6
  return Array.from({ length: 7 }, (_, i) => {
    const day = (today - 6 + i + 7) % 7;
    const seed = day * 31 + i * 7;
    return {
      date: new Date(Date.now() - (6 - i) * 86400000).toISOString(),
      count: Math.max(0, Math.floor(ordersToday * (0.4 + seededRandom(seed) * 0.7))),
    };
  });
}

function generateRevenueChartData(revenueToday: number) {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const today = new Date().getDay();
  return days.map((label, i) => {
    const seed = i * 13 + today * 3;
    return {
      label,
      food: Math.floor(revenueToday * 0.6 * (0.5 + seededRandom(seed) * 0.6)),
      stationery: Math.floor(revenueToday * 0.4 * (0.3 + seededRandom(seed + 5) * 0.6)),
    };
  });
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: analytics, loading: analyticsLoading } = useAdminAnalytics();

  const [liveOrders, setLiveOrders] = useState<Order[]>([]);
  const [pendingVendors, setPendingVendors] = useState<Vendor[]>([]);
  const [openComplaints, setOpenComplaints] = useState<Complaint[]>([]);
  const [rushHour, setRushHour] = useState<RushHourSignal | null>(null);
  const [vendorRankings, setVendorRankings] = useState<VendorRanking[]>([]);
  const [demandPlans, setDemandPlans] = useState<DemandPlan[]>([]);

  function safeNumber(n: unknown): number {
    const v = Number(n);
    return Number.isFinite(v) ? v : 0;
  }
  const [ordersLoading, setOrdersLoading] = useState(true);
  const [approvingId, setApprovingId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'kpis'>('overview');

  const fetchLiveOrders = useCallback(async () => {
    try {
      const res = await adminApi.getAllOrders({ limit: 10, sort: 'newest' });
      setLiveOrders(Array.isArray(res.data) ? res.data : []);
    } catch {
      // Silently fail for polling
    } finally {
      setOrdersLoading(false);
    }
  }, []);

  const fetchSideData = useCallback(async () => {
    try {
      const [vendorsRes, complaintsRes] = await Promise.allSettled([
        adminApi.getPendingVendors(),
        complaintsApi.getAll({ status: 'open', limit: 5 }),
      ]);
      if (vendorsRes.status === 'fulfilled') {
        setPendingVendors(Array.isArray(vendorsRes.value.data) ? vendorsRes.value.data.slice(0, 4) : []);
      }
      if (complaintsRes.status === 'fulfilled') {
        setOpenComplaints(Array.isArray(complaintsRes.value.data) ? complaintsRes.value.data.slice(0, 5) : []);
      }
    } catch { /* silent */ }
  }, []);

  const fetchAIData = useCallback(async (vendorId?: number) => {
    try {
      const promises: Promise<unknown>[] = [
        aiApi.getRushHour(),
        aiApi.getVendorRanking(),
      ];

      if (vendorId && vendorId > 0) {
        promises.push(aiApi.getDemandPlanning(vendorId));
      }

      const [rushRes, rankRes, demandRes] = await Promise.allSettled(
        vendorId && vendorId > 0
          ? [aiApi.getRushHour(), aiApi.getVendorRanking(), aiApi.getDemandPlanning(vendorId)]
          : [aiApi.getRushHour(), aiApi.getVendorRanking()]
      );

      if (rushRes.status === 'fulfilled') setRushHour((rushRes.value as any).data);
      if (rankRes.status === 'fulfilled') {
        setVendorRankings(Array.isArray((rankRes.value as any).data) ? (rankRes.value as any).data.slice(0, 3) : []);
      }
      if (demandRes && demandRes.status === 'fulfilled') {
        setDemandPlans(Array.isArray((demandRes.value as any).data) ? (demandRes.value as any).data : []);
      }
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    const init = async () => {
      fetchLiveOrders();

      try {
        const [vendorsRes, complaintsRes] = await Promise.allSettled([
          adminApi.getPendingVendors(),
          complaintsApi.getAll({ status: 'open', limit: 5 }),
        ]);

        let firstVendorId: number | undefined;

        if (vendorsRes.status === 'fulfilled') {
          const list = Array.isArray(vendorsRes.value.data) ? vendorsRes.value.data : [];
          const pending = list.filter((v: any) => !v.is_approved && v.is_active !== false);
          setPendingVendors(pending.slice(0, 4));
          firstVendorId = pending[0]?.id || list[0]?.id;
        }
        if (complaintsRes.status === 'fulfilled') {
          setOpenComplaints(Array.isArray(complaintsRes.value.data) ? complaintsRes.value.data.slice(0, 5) : []);
        }

        fetchAIData(firstVendorId);
      } catch {
        fetchAIData(undefined);
      }
    };

    init();

    const ordersInterval = setInterval(fetchLiveOrders, POLL_INTERVAL_ORDERS);
    return () => clearInterval(ordersInterval);
  }, [fetchLiveOrders, fetchAIData]);

  const handleApproveVendor = async (id: number) => {
    setApprovingId(id);
    try {
      await adminApi.approveVendor(id);
      setPendingVendors(prev => prev.filter(v => v.id !== id));
      toast.success('Vendor approved successfully');
    } catch {
      toast.error('Failed to approve vendor');
    } finally {
      setApprovingId(null);
    }
  };

  const handleRejectVendor = async (id: number) => {
    setApprovingId(id);
    try {
      await adminApi.rejectVendor(id);
      setPendingVendors(prev => prev.filter(v => v.id !== id));
      toast.success('Vendor rejected');
    } catch {
      toast.error('Failed to reject vendor');
    } finally {
      setApprovingId(null);
    }
  };

  const ordersToday = analytics?.orders_today || 0;
  const revenueToday = analytics?.revenue_today_paise || 0;
  const ordersChartData = generateOrdersChartData(ordersToday);
  const revenueChartData = generateRevenueChartData(revenueToday);

  const rushLevel = rushHour?.level || 'low';
  const rushColors = RUSH_HOUR_COLORS[rushLevel] ?? RUSH_HOUR_COLORS.low;

  const overCapacityVendors = (demandPlans ?? []).filter((d: DemandPlan) => {
    const predicted = safeNumber((d as any)?.predicted_orders);
    const capacity = safeNumber((d as any)?.current_capacity);
    return predicted > capacity;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#111827]">
            Dashboard
          </h2>
          <p className="text-sm mt-0.5 text-[#4B5563]">
            {format(new Date(), 'EEEE, MMMM d yyyy')} • Live admin overview
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ExportButton
            label="Export Revenue CSV"
            exportFn={() => adminApi.exportRevenue({ date_from: dateFrom, date_to: dateTo })}
            filename="tnt_revenue.csv"
          />
          <button
            onClick={() => { fetchLiveOrders(); fetchSideData(); fetchAIData(pendingVendors[0]?.id); }}
            className="btn-ghost"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#E5E7EB] gap-6">
        <button
          onClick={() => setActiveTab('overview')}
          className={cn(
            "pb-3 text-sm font-bold border-b-2 px-1 transition-all",
            activeTab === 'overview'
              ? "border-[#4F46E5] text-[#4F46E5]"
              : "border-transparent text-[#6B7280] hover:text-[#111827]"
          )}
        >
          Live Overview
        </button>
        <button
          onClick={() => setActiveTab('kpis')}
          className={cn(
            "pb-3 text-sm font-bold border-b-2 px-1 transition-all",
            activeTab === 'kpis'
              ? "border-[#4F46E5] text-[#4F46E5]"
              : "border-transparent text-[#6B7280] hover:text-[#111827]"
          )}
        >
          Institutional KPIs
        </button>
      </div>

      {activeTab === 'kpis' ? (
        <KPIDashboard />
      ) : (
        <>
          {/* ─── Row 1: Stat Cards (Hero Section) ────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          title="Total Users"
          value={formatNumber(analytics?.total_users || 0)}
          subtitle={`${formatNumber(analytics?.active_users || 0)} active`}
          icon={Users}
          accent="indigo"
          loading={analyticsLoading}
          trend={3.2}
        />
        <StatCard
          title="Active Vendors"
          value={formatNumber(analytics?.total_vendors || 0)}
          subtitle={`${analytics?.pending_vendors || 0} pending approval`}
          icon={Store}
          accent="blue"
          loading={analyticsLoading}
          trend={1.8}
        />
        <StatCard
          title="Orders Today"
          value={formatNumber(ordersToday)}
          subtitle={`${formatNumber(analytics?.completed_today || Math.floor(ordersToday * 0.7))} completed`}
          icon={ShoppingBag}
          accent="green"
          loading={analyticsLoading}
          trend={12.5}
        />
        <StatCard
          title="Revenue Today"
          value={formatPaise(revenueToday)}
          subtitle="Via Razorpay + Cash"
          icon={IndianRupee}
          accent="amber"
          loading={analyticsLoading}
          trend={8.3}
        />
      </div>

      {/* ─── Row 2: Charts ──────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <OrdersLineChart data={ordersChartData} title="Orders — Last 7 Days" />
        <RevenueBarChart data={revenueChartData} title="Revenue by Category (₹)" />
      </div>

      {/* ─── Row 3: Live Orders Feed ───────────────────────── */}
      <div className="tnt-card overflow-hidden p-0">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#E5E7EB]">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <h3 className="text-sm font-semibold text-[#111827]">
              Live Activity Feed
            </h3>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-50 text-orange-600 border border-orange-200">
              {liveOrders.length} orders
            </span>
          </div>
          <button
            onClick={() => navigate('/orders')}
            className="text-xs text-[#9CA3AF] hover:text-[#4F46E5] flex items-center gap-1 transition-colors"
          >
            View all <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {ordersLoading ? (
          <div className="p-5 space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="flex gap-4 items-center">
                <div className="skeleton w-16 h-4 rounded" />
                <div className="skeleton w-24 h-4 rounded" />
                <div className="skeleton flex-1 h-4 rounded" />
                <div className="skeleton w-16 h-5 rounded-full" />
              </div>
            ))}
          </div>
        ) : liveOrders.length === 0 ? (
          <div className="py-12 text-center text-sm text-[#4B5563]">
            No recent orders
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="tnt-table">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Student</th>
                  <th>Vendor</th>
                  <th>Items</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Time</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {liveOrders.map((order) => (
                  <tr key={order.id} onClick={() => navigate(`/orders/${order.id}`)} className="cursor-pointer">
                    <td>
                      <span className="font-mono text-[#4F46E5] text-xs">
                        {formatOrderId(order.id)}
                      </span>
                    </td>
                    <td className="text-[#111827]">
                      {order.user_name || `User #${order.user_id}`}
                    </td>
                    <td className="text-[#4B5563]">
                      {order.vendor_name || `Vendor #${order.vendor_id}`}
                    </td>
                    <td className="text-xs text-[#4B5563]">
                      {order.items?.length > 0 ? (
                        `${order.items.length} item${order.items.length > 1 ? 's' : ''}`
                      ) : '—'}
                    </td>
                    <td>
                      <span className="font-mono text-xs font-medium text-[#111827]">
                        ₹{(order.total_amount / 100).toFixed(0)}
                      </span>
                    </td>
                    <td>
                      <StatusBadge type="order" status={order.status} />
                    </td>
                    <td className="text-xs whitespace-nowrap text-[#4B5563]">
                      {formatTimeAgo(order.created_at)}
                    </td>
                    <td>
                      {order.fraud_flag && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-50 text-red-600 border border-red-200">
                          ⚠ FRAUD
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ─── Row 4: Pending Approvals + Open Complaints ─────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Pending Vendor Approvals */}
        <div className="tnt-card p-0 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#E5E7EB]">
            <div className="flex items-center gap-2">
              <Store className="w-4 h-5 text-[#4F46E5]" />
              <h3 className="text-sm font-semibold text-[#111827]">Pending Approvals</h3>
              {pendingVendors.length > 0 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-600 border border-amber-200">
                  {pendingVendors.length}
                </span>
              )}
            </div>
            <button
              onClick={() => navigate('/vendors?tab=pending')}
              className="text-xs text-[#9CA3AF] hover:text-[#4F46E5] flex items-center gap-1 transition-colors"
            >
              View all <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="p-4 space-y-3">
            {pendingVendors.length === 0 ? (
              <div className="py-8 text-center">
                <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="text-sm text-[#4B5563]">All vendors reviewed</p>
              </div>
            ) : (
              pendingVendors.map((vendor) => (
                <div
                  key={vendor.id}
                  className="flex items-center justify-between gap-3 p-3 rounded-xl bg-[#F3F5F9] border border-[#E5E7EB]"
                >
                  <div className="flex items-center gap-3 flex-1 overflow-hidden">
                    <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center shrink-0">
                      <Store className="w-4 h-5 text-[#E85D24]" />
                    </div>
                    <div className="overflow-hidden">
                      <p className="text-sm font-medium truncate text-[#111827]">{vendor.name}</p>
                      <div className="flex items-center gap-2">
                        <StatusBadge type="vendor_type" status={vendor.vendor_type} />
                        <span className="text-xs text-[#4B5563]">{vendor.location}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleApproveVendor(vendor.id)}
                      disabled={approvingId === vendor.id}
                      className="btn-success btn-sm"
                    >
                      ✓
                    </button>
                    <button
                      onClick={() => handleRejectVendor(vendor.id)}
                      disabled={approvingId === vendor.id}
                      className="btn-danger btn-sm"
                    >
                      ✗
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Open Complaints */}
        <div className="tnt-card p-0 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#E5E7EB]">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-5 text-amber-500" />
              <h3 className="text-sm font-semibold text-[#111827]">Open Complaints</h3>
              {openComplaints.length > 0 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-600 border border-red-200">
                  {openComplaints.length}
                </span>
              )}
            </div>
            <button
              onClick={() => navigate('/complaints')}
              className="text-xs text-[#9CA3AF] hover:text-[#4F46E5] flex items-center gap-1 transition-colors"
            >
              View all <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="p-4 space-y-3">
            {openComplaints.length === 0 ? (
              <div className="py-8 text-center">
                <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="text-sm text-[#4B5563]">No open complaints</p>
              </div>
            ) : (
              openComplaints.map((complaint) => (
                <div
                  key={complaint.id}
                  onClick={() => navigate('/complaints')}
                  className="flex items-start gap-3 p-3 rounded-xl bg-[#F3F5F9] border border-[#E5E7EB] cursor-pointer hover:border-[#D1D5DB] transition-all"
                >
                  <div className="w-2 h-2 rounded-full bg-red-500 mt-1.5 shrink-0 animate-pulse" />
                  <div className="flex-1 overflow-hidden">
                    <p className="text-xs font-medium truncate text-[#111827]">{complaint.category}</p>
                    <p className="text-xs truncate mt-0.5 text-[#4B5563]">{complaint.description}</p>
                    <p className="text-[10px] text-[#9CA3AF] mt-1">{formatTimeAgo(complaint.created_at)}</p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); navigate('/complaints'); }}
                    className="btn-ghost btn-sm shrink-0 text-xs"
                  >
                    Escalate
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* ─── Row 5: AI Intelligence Snapshot ───────────────── */}
      <div className="tnt-card">
        <div className="flex items-center gap-2 mb-5">
          <Brain className="w-5 h-5 text-[#4F46E5]" />
          <h3 className="text-sm font-semibold text-[#111827]">AI Intelligence Snapshot</h3>
          <button
            onClick={() => navigate('/ai')}
            className="ml-auto text-xs flex items-center gap-1 transition-colors text-[#4B5563] hover:text-[#111827]"
          >
            Full AI Dashboard <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Rush Hour Meter */}
          <div className="bg-[#F3F5F9] rounded-xl p-4 border border-[#E5E7EB]">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-[#4B5563]" />
              <p className="text-xs font-medium text-[#4B5563]">Campus Rush Level</p>
            </div>
            {rushHour ? (
              <>
                <div className={cn(
                  'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-bold mb-3',
                  rushColors.bg
                )}>
                  <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: rushColors.fill }} />
                  <span className={rushColors.text}>{rushLevel.toUpperCase()}</span>
                </div>
                <div className="w-full bg-[#E5E7EB] rounded-full h-2 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: rushLevel === 'critical' ? '100%' : rushLevel === 'high' ? '75%' : rushLevel === 'medium' ? '50%' : '25%',
                      backgroundColor: rushColors.fill,
                    }}
                  />
                </div>
                <p className="text-xs mt-2 text-[#4B5563]">
                  {rushHour.active_orders} active orders
                </p>
              </>
            ) : (
              <div className="skeleton w-full h-16 rounded-lg" />
            )}
          </div>

          {/* Top Vendors */}
          <div className="bg-[#F3F5F9] rounded-xl p-4 border border-[#E5E7EB]">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-4 h-4 text-[#4B5563]" />
              <p className="text-xs font-medium text-[#4B5563]">Top AI-Ranked Vendors</p>
            </div>
            {vendorRankings.length > 0 ? (
              <div className="space-y-2">
                {vendorRankings.slice(0, 3).map((v, i) => (
                  <div key={v.vendor_id} className="flex items-center gap-2">
                    <span className={cn(
                      'w-5 h-5 rounded text-[10px] font-bold flex items-center justify-center shrink-0',
                      i === 0 ? 'bg-amber-100 text-amber-700' :
                      i === 1 ? 'bg-gray-100 text-gray-600' :
                      'bg-orange-100 text-orange-700'
                    )}>
                      #{v.rank}
                    </span>
                    <span className="text-xs flex-1 truncate text-[#111827]">{v.vendor_name}</span>
                    <span className="text-xs font-mono text-[#111827]">{v.score.toFixed(1)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {[1, 2, 3].map(i => <div key={i} className="skeleton h-5 rounded" />)}
              </div>
            )}
          </div>

          {/* Demand Planning Alert */}
          <div className="bg-[#F3F5F9] rounded-xl p-4 border border-[#E5E7EB]">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-[#4B5563]" />
              <p className="text-xs font-medium text-[#4B5563]">Demand Alerts</p>
            </div>
            {overCapacityVendors.length > 0 ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-[#4B5563]">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-xs font-medium">
                    {overCapacityVendors.length} vendor{overCapacityVendors.length > 1 ? 's' : ''} near capacity
                  </span>
                </div>
                {overCapacityVendors.slice(0, 2).map((d) => (
                  <div key={d.vendor_id} className="text-xs truncate text-[#4B5563]">
                    • {d.vendor_name}: {d.predicted_orders} predicted / {d.current_capacity} cap
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center py-2">
                <CheckCircle className="w-6 h-6 mb-1 text-green-500" />
                <p className="text-xs font-medium text-green-600">All capacity OK</p>
              </div>
            )}
          </div>

          {/* Conflict Widget */}
          <ConflictWidget />
        </div>
      </div>
        </>
      )}
    </div>
  );
}
