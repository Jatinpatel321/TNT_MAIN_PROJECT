import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  AlertTriangle, ShieldCheck, ShieldAlert, Users, 
  Search, ShieldAlert as Siren, RefreshCw, Eye, 
  ChevronLeft, ChevronRight, CheckCircle2, AlertOctagon 
} from 'lucide-react';
import toast from 'react-hot-toast';
import { 
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';
import { adminApi } from '../../api/admin';
import { formatDate } from '../../utils/format';
import type { FraudAlert, FraudMetrics } from '../../types';

const SEVERITY_COLORS = {
  low: '#10B981',      // Emerald/Green
  medium: '#F59E0B',   // Amber/Orange
  high: '#EF4444',     // Red
  critical: '#7F1D1D', // Dark Red
};

export default function FraudDashboard() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<FraudMetrics | null>(null);
  const [alertsData, setAlertsData] = useState<{ alerts: FraudAlert[]; total: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const totalPages = alertsData ? Math.ceil(alertsData.total / 10) : 0;

  // Filter states
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('pending');

  const fetchMetrics = useCallback(async () => {
    try {
      const res = await adminApi.getFraudMetrics();
      setMetrics(res.data);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load fraud metrics');
    }
  }, []);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 10 };
      if (search) params.search = search;
      if (typeFilter) params.alert_type = typeFilter;
      if (severityFilter) params.severity = severityFilter;
      if (statusFilter !== 'all') params.status = statusFilter;

      const res = await adminApi.getFraudAlerts(params);
      setAlertsData(res.data);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load fraud alerts');
    } finally {
      setLoading(false);
    }
  }, [page, search, typeFilter, severityFilter, statusFilter]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleRunScan = async () => {
    setScanning(true);
    try {
      const res = await adminApi.triggerFraudScan();
      toast.success(`Scan complete! Found ${res.data.alerts_found} new alerts.`);
      fetchMetrics();
      fetchAlerts();
    } catch {
      toast.error('Failed to run diagnostic scan');
    } finally {
      setScanning(false);
    }
  };

  // Process data for charts
  const severityChartData = metrics ? Object.entries(metrics.severity_distribution).map(([name, value]) => ({
    name: name.toUpperCase(),
    value,
    color: SEVERITY_COLORS[name as keyof typeof SEVERITY_COLORS] || '#6366F1',
  })).filter(item => item.value > 0) : [];

  const typeChartData = metrics ? Object.entries(metrics.type_distribution).map(([name, value]) => ({
    name: name.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()),
    count: value,
  })) : [];

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#111827]">Fraud Detection System</h1>
          <p className="text-sm text-[#4B5563]">Monitor transaction anomalies, account integrity, and user behaviors</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/fraud/investigate')}
            className="inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-xl border border-[#D1D5DB] bg-white text-[#4B5563] hover:bg-[#F3F5F9] transition-all"
          >
            <Search className="w-4 h-4" />
            Workspace Investigator
          </button>
          <button
            onClick={handleRunScan}
            disabled={scanning}
            className="btn-primary inline-flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
            {scanning ? 'Auditing System...' : 'Run Diagnostics Scan'}
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="stat-card flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-[#6B7280]">Pending Alerts</p>
              <p className="text-2xl font-bold text-[#111827] mt-1">{metrics.summary.pending_alerts}</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center text-[#E85D24]">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>

          <div className="stat-card flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-[#6B7280]">Critical Incidents</p>
              <p className="text-2xl font-bold text-[#7F1D1D] mt-1">{metrics.summary.critical_alerts}</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center text-[#EF4444]">
              <AlertOctagon className="w-5 h-5" />
            </div>
          </div>

          <div className="stat-card flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-[#6B7280]">Blacklisted Accounts</p>
              <p className="text-2xl font-bold text-[#111827] mt-1">
                {metrics.summary.blacklisted_users + metrics.summary.blacklisted_vendors}
              </p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center text-[#4F46E5]">
              <Users className="w-5 h-5" />
            </div>
          </div>

          <div className="stat-card flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-[#6B7280]">Resolved Anomalies</p>
              <p className="text-2xl font-bold text-[#111827] mt-1">{metrics.summary.resolved_alerts}</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center text-[#22C55E]">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
        </div>
      )}

      {/* Chart Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="tnt-card lg:col-span-1 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-[#111827] mb-1">Severity Distribution</h3>
            <p className="text-xs text-[#6B7280] mb-4">Proportion of pending security concerns by threat severity</p>
          </div>
          {severityChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={severityChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {severityChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center border border-dashed border-[#E5E7EB] rounded-xl text-xs text-[#9CA3AF]">
              No pending alerts to map
            </div>
          )}
        </div>

        <div className="tnt-card lg:col-span-2 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-[#111827] mb-1">Common Abuse Vectors</h3>
            <p className="text-xs text-[#6B7280] mb-4">Total incidence volume across all fraud categories</p>
          </div>
          {typeChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={typeChartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#4F46E5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center border border-dashed border-[#E5E7EB] rounded-xl text-xs text-[#9CA3AF]">
              No alert metrics logged yet
            </div>
          )}
        </div>
      </div>

      {/* Filters and List */}
      <div className="tnt-card">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
          <h3 className="font-semibold text-base text-[#111827]">Anomalous Event Feed</h3>
          <div className="w-full md:w-auto flex flex-wrap gap-2">
            {/* Search */}
            <div className="relative w-full sm:w-64">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-[#9CA3AF]">
                <Search className="w-4 h-4" />
              </span>
              <input
                type="text"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                placeholder="Search descriptions..."
                className="w-full text-xs border border-[#E5E7EB] bg-white rounded-xl pl-9 pr-4 py-2 focus:ring-1 focus:ring-[#4F46E5] focus:border-[#4F46E5] outline-none text-[#111827]"
              />
            </div>

            {/* Severity Filter */}
            <select
              value={severityFilter}
              onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
              className="text-xs border border-[#E5E7EB] bg-white rounded-xl px-3 py-2 outline-none text-[#111827]"
            >
              <option value="">All Severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>

            {/* Alert Type Filter */}
            <select
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
              className="text-xs border border-[#E5E7EB] bg-white rounded-xl px-3 py-2 outline-none text-[#111827]"
            >
              <option value="">All Categories</option>
              <option value="duplicate_orders">Duplicate Orders</option>
              <option value="repeated_refunds">Repeated Refunds</option>
              <option value="suspicious_logins">Suspicious Logins</option>
              <option value="abnormal_vendor">Abnormal Vendor</option>
              <option value="fake_account">Fake Account</option>
              <option value="coupon_abuse">Coupon Abuse</option>
              <option value="reward_abuse">Reward Abuse</option>
              <option value="payment_abuse">Payment Abuse</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="text-xs border border-[#E5E7EB] bg-white rounded-xl px-3 py-2 outline-none text-[#111827]"
            >
              <option value="pending">Pending Review</option>
              <option value="resolved">Resolved</option>
              <option value="false_positive">False Positives</option>
              <option value="all">All Logs</option>
            </select>
          </div>
        </div>

        {/* Table List */}
        {loading ? (
          <div className="py-20 text-center text-[#6B7280]">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-[#4F46E5] mb-2" />
            <p className="text-xs">Gathering audit details...</p>
          </div>
        ) : alertsData && alertsData.alerts.length > 0 ? (
          <div className="overflow-x-auto -mx-6">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#F8FAFC] border-y border-[#E5E7EB] text-xs font-semibold text-[#4B5563]">
                  <th className="px-6 py-3">Severity</th>
                  <th className="px-6 py-3">Vector Type</th>
                  <th className="px-6 py-3">Incident Explanation</th>
                  <th className="px-6 py-3">User / Vendor</th>
                  <th className="px-6 py-3">Logged Date</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E7EB]">
                {alertsData.alerts.map((alert) => (
                  <tr key={alert.id} className="hover:bg-[#F3F5F9] text-xs text-[#111827] transition-colors">
                    <td className="px-6 py-4">
                      <span 
                        className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border"
                        style={{
                          color: SEVERITY_COLORS[alert.severity as keyof typeof SEVERITY_COLORS],
                          borderColor: `${SEVERITY_COLORS[alert.severity as keyof typeof SEVERITY_COLORS]}30`,
                          backgroundColor: `${SEVERITY_COLORS[alert.severity as keyof typeof SEVERITY_COLORS]}10`,
                        }}
                      >
                        {alert.severity.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono font-medium text-[#4B5563]">
                      {alert.alert_type}
                    </td>
                    <td className="px-6 py-4 max-w-sm truncate text-[#4B5563]" title={alert.description}>
                      {alert.description}
                    </td>
                    <td className="px-6 py-4">
                      {alert.user_name ? (
                        <div>
                          <p className="font-semibold text-[#111827]">{alert.user_name}</p>
                          <p className="text-[10px] text-[#6B7280]">{alert.user_phone}</p>
                        </div>
                      ) : alert.vendor_name ? (
                        <p className="font-semibold text-[#111827]">{alert.vendor_name}</p>
                      ) : (
                        <span className="text-[#9CA3AF]">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-[#6B7280]">
                      {formatDate(alert.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                        alert.status === 'pending' ? 'bg-orange-50 text-orange-700 border-orange-200' :
                        alert.status === 'resolved' ? 'bg-green-50 text-green-700 border-green-200' :
                        'bg-slate-50 text-slate-600 border-slate-200'
                      }`}>
                        {alert.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => navigate(`/fraud/${alert.id}`)}
                        className="inline-flex items-center gap-1 text-[#4F46E5] hover:text-[#4338CA] font-medium transition-all"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Investigate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-20 text-center border border-dashed border-[#E5E7EB] rounded-2xl">
            <CheckCircle2 className="w-10 h-10 text-[#22C55E] mx-auto mb-3" />
            <p className="text-sm font-semibold text-[#111827]">Zero Anomalies Found</p>
            <p className="text-xs text-[#6B7280] mt-1">All processed transactions conform to secure parameters.</p>
          </div>
        )}

        {/* Pagination */}
        {alertsData && totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-[#E5E7EB] pt-4 mt-6">
            <span className="text-xs text-[#6B7280]">
              Showing page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(prev => Math.max(prev - 1, 1))}
                disabled={page === 1}
                className="inline-flex items-center justify-center p-2 border border-[#E5E7EB] rounded-xl hover:bg-[#F3F5F9] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(prev => Math.min(prev + 1, totalPages))}
                disabled={page === totalPages}
                className="inline-flex items-center justify-center p-2 border border-[#E5E7EB] rounded-xl hover:bg-[#F3F5F9] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
