import React, { useState, useEffect } from 'react';
import { Shield, Search, ChevronLeft, ChevronRight, Clock, User, Package, Tag, FileText, Megaphone, LogIn, Download, BarChart2, Activity } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import { cn } from '../../utils/cn';

interface AuditLogEntry {
  id: number;
  actor_id: number | null;
  actor_name: string | null;
  actor_role: string | null;
  action: string;
  action_category: string;
  entity_type: string | null;
  entity_id: string | null;
  before_state: any;
  after_state: any;
  ip_address: string | null;
  created_at: string;
}

const CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'auth', label: 'Authentication', icon: LogIn },
  { value: 'user', label: 'Users', icon: User },
  { value: 'vendor', label: 'Vendors', icon: Package },
  { value: 'order', label: 'Orders', icon: FileText },
  { value: 'inventory', label: 'Inventory', icon: Package },
  { value: 'menu', label: 'Menu', icon: FileText },
  { value: 'payment', label: 'Payments', icon: FileText },
  { value: 'policy', label: 'Policies', icon: Shield },
  { value: 'voucher', label: 'Vouchers', icon: Tag },
  { value: 'announcement', label: 'Announcements', icon: Megaphone },
];

const ROLES = [
  { value: '', label: 'All Roles' },
  { value: 'admin', label: 'Admin' },
  { value: 'vendor', label: 'Vendor' },
  { value: 'student', label: 'Student' },
  { value: 'faculty', label: 'Faculty' },
  { value: 'staff', label: 'Staff' },
];

const CATEGORY_STYLES: Record<string, string> = {
  auth: 'bg-blue-50 text-blue-700 border-blue-200',
  user: 'bg-purple-50 text-purple-700 border-purple-200',
  vendor: 'bg-amber-50 text-amber-700 border-amber-200',
  order: 'bg-green-50 text-green-700 border-green-200',
  inventory: 'bg-teal-50 text-teal-700 border-teal-200',
  menu: 'bg-orange-50 text-orange-700 border-orange-200',
  payment: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  policy: 'bg-red-50 text-red-700 border-red-200',
  voucher: 'bg-pink-50 text-pink-700 border-pink-200',
  announcement: 'bg-indigo-50 text-indigo-700 border-indigo-200',
};

const humanizeAction = (action: string) =>
  action
    .replace(/\./g, ' → ')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

export default function AuditLogs() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'timeline'>('dashboard');

  // Timeline State
  const [logs, setLogs] = useState([] as AuditLogEntry[]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [category, setCategory] = useState('');
  const [role, setRole] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [expandedRow, setExpandedRow] = useState(null as number | null);
  const [exporting, setExporting] = useState(false);

  // Stats State
  const [stats, setStats] = useState<any>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [category, role, dateFrom, dateTo]);

  useEffect(() => {
    if (activeTab === 'timeline') {
      fetchLogs();
    } else {
      fetchStats();
    }
  }, [activeTab, page, debouncedSearch, category, role, dateFrom, dateTo]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 50 };
      if (debouncedSearch) params.search = debouncedSearch;
      if (category) params.action_category = category;
      if (role) params.actor_role = role;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const res = await adminApi.getAuditLogs(params);
      setLogs(res.data.logs || []);
      setTotal(res.data.total || 0);
      setTotalPages(res.data.total_pages || 1);
    } catch {
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const res = await adminApi.getAuditStats();
      setStats(res.data);
    } catch {
      toast.error('Failed to load audit stats');
    } finally {
      setLoadingStats(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const params: any = {};
      if (category) params.action_category = category;
      if (role) params.actor_role = role;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const res = await adminApi.exportAuditLogs(params);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      toast.success('Export successful');
    } catch (e) {
      toast.error('Failed to export logs');
    } finally {
      setExporting(false);
    }
  };

  const formatTimestamp = (iso: string) => {
    const d = new Date(iso);
    return {
      date: d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }),
      time: d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }),
    };
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 rounded-lg text-[#4F46E5]">
            <Shield className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-[#111827]">Compliance & Audit</h2>
            <p className="text-sm text-[#6B7280]">Immutable tracking across all system modules</p>
          </div>
        </div>

        {/* Tab Selector */}
        <div className="flex bg-[#F3F5F9] p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              activeTab === 'dashboard' ? "bg-white text-[#4F46E5] shadow-sm" : "text-[#6B7280] hover:text-[#111827]"
            )}
          >
            <BarChart2 className="w-4 h-4" /> Dashboard
          </button>
          <button
            onClick={() => setActiveTab('timeline')}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              activeTab === 'timeline' ? "bg-white text-[#4F46E5] shadow-sm" : "text-[#6B7280] hover:text-[#111827]"
            )}
          >
            <Activity className="w-4 h-4" /> Timeline
          </button>
        </div>
      </div>

      {activeTab === 'dashboard' && (
        <div className="space-y-6">
          {loadingStats ? (
            <div className="p-10 flex justify-center">
              <div className="w-6 h-6 border-2 border-[#2E2E50] border-t-[#4F46E5] rounded-full animate-spin" />
            </div>
          ) : stats ? (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="tnt-card">
                  <p className="text-sm font-medium text-[#6B7280]">Events (30 Days)</p>
                  <p className="text-3xl font-bold text-[#111827] mt-1">{stats.total_logs_30d.toLocaleString()}</p>
                </div>
                <div className="tnt-card">
                  <p className="text-sm font-medium text-[#6B7280]">Active Actors (30 Days)</p>
                  <p className="text-3xl font-bold text-[#111827] mt-1">{stats.active_users_30d.toLocaleString()}</p>
                </div>
                <div className="tnt-card">
                  <p className="text-sm font-medium text-[#6B7280]">Critical Actions</p>
                  <p className="text-3xl font-bold text-[#EF4444] mt-1">{stats.critical_actions_30d.toLocaleString()}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Events by Category */}
                <div className="tnt-card">
                  <h3 className="text-lg font-semibold text-[#111827] mb-4">Events by Category</h3>
                  <div className="space-y-4">
                    {Object.entries(stats.actions_by_category).map(([cat, count]: [string, any]) => {
                      const percentage = Math.round((count / stats.total_logs_30d) * 100);
                      return (
                        <div key={cat}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="font-medium text-[#4B5563]">{cat}</span>
                            <span className="text-[#6B7280]">{count} ({percentage}%)</span>
                          </div>
                          <div className="w-full bg-[#E5E7EB] rounded-full h-2">
                            <div className="bg-[#4F46E5] h-2 rounded-full" style={{ width: `${percentage}%` }}></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Daily Trend */}
                <div className="tnt-card">
                  <h3 className="text-lg font-semibold text-[#111827] mb-4">30-Day Activity Trend</h3>
                  <div className="h-64 flex items-end justify-between gap-1 mt-6">
                    {stats.actions_by_day.map((d: any) => {
                      const max = Math.max(...stats.actions_by_day.map((x: any) => x.count), 1);
                      const height = `${Math.max((d.count / max) * 100, 2)}%`;
                      return (
                        <div key={d.date} className="relative group w-full flex justify-center">
                          <div 
                            className="w-full bg-[#818CF8] hover:bg-[#4F46E5] rounded-t-sm transition-colors" 
                            style={{ height }}
                          ></div>
                          <div className="absolute bottom-full mb-2 hidden group-hover:block z-10">
                            <div className="bg-[#111827] text-white text-xs px-2 py-1 rounded shadow-lg whitespace-nowrap">
                              {d.date}: {d.count} events
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </>
          ) : (
             <div className="py-16 text-center text-sm text-[#6B7280]">
               Failed to load dashboard data.
             </div>
          )}
        </div>
      )}

      {activeTab === 'timeline' && (
        <div className="space-y-4">
          <div className="tnt-card flex flex-wrap gap-3 items-end">
            <div className="relative min-w-[200px] flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
              <input
                type="text"
                placeholder="Search by action or entity..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="tnt-input pl-9"
              />
            </div>
            
            <div className="flex gap-2 w-full md:w-auto">
              <select value={category} onChange={(e) => setCategory(e.target.value)} className="tnt-select min-w-[140px]">
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
              <select value={role} onChange={(e) => setRole(e.target.value)} className="tnt-select min-w-[120px]">
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2 text-sm text-[#6B7280] w-full md:w-auto">
              <span>From</span>
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="tnt-input py-2" />
              <span>To</span>
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="tnt-input py-2" />
            </div>

            <button 
              onClick={handleExport}
              disabled={exporting || total === 0}
              className="tnt-button-secondary ml-auto md:ml-0"
            >
              {exporting ? 'Exporting...' : <><Download className="w-4 h-4 mr-1" /> Export CSV</>}
            </button>
          </div>

          <p className="text-sm text-[#6B7280]">{total.toLocaleString()} entries found</p>

          <div className="tnt-card overflow-hidden p-0">
            {loading ? (
              <div className="p-10 flex justify-center">
                <div className="w-6 h-6 border-2 border-[#2E2E50] border-t-[#E85D24] rounded-full animate-spin" />
              </div>
            ) : logs.length === 0 ? (
              <div className="py-16 text-center text-sm text-[#6B7280]">
                No audit log entries match the current filters.
              </div>
            ) : (
              <div className="divide-y divide-[#E5E7EB]">
                {logs.map((log: AuditLogEntry) => {
                  const { date, time } = formatTimestamp(log.created_at);
                  const isExpanded = expandedRow === log.id;
                  const catStyle = CATEGORY_STYLES[log.action_category] || 'bg-gray-50 text-gray-600 border-gray-200';

                  return (
                    <div key={log.id}>
                      <button
                        onClick={() => setExpandedRow(isExpanded ? null : log.id)}
                        className="w-full flex items-start gap-4 px-5 py-4 hover:bg-[#F3F5F9] transition-colors text-left"
                      >
                        <div className="mt-1 flex flex-col items-center shrink-0">
                          <div className="h-2.5 w-2.5 rounded-full bg-[#4F46E5]" />
                          <div className="w-px flex-1 bg-[#E5E7EB] mt-1 min-h-[1.5rem]" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wide', catStyle)}>
                              {log.action_category}
                            </span>
                            <span className="text-sm font-semibold text-[#111827]">{humanizeAction(log.action)}</span>
                            {log.entity_type && log.entity_id && (
                              <span className="text-xs font-mono bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                                {log.entity_type} #{log.entity_id}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-4 mt-2 text-xs text-[#6B7280]">
                            <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{date} {time}</span>
                            {log.actor_id ? (
                               <span className="flex items-center gap-1 bg-[#F3F4F6] px-2 py-0.5 rounded">
                                 <User className="h-3 w-3 text-[#9CA3AF]" />
                                 <span className="font-medium text-[#374151]">
                                   {log.actor_name || `User ${log.actor_id}`}
                                 </span>
                                 {log.actor_role && <span className="text-[#9CA3AF] capitalize">({log.actor_role})</span>}
                               </span>
                            ) : (
                               <span className="flex items-center gap-1 bg-red-50 text-red-600 px-2 py-0.5 rounded">
                                 System / Anonymous
                               </span>
                            )}
                            {log.ip_address && <span className="hidden sm:inline">IP: {log.ip_address}</span>}
                            <span className="ml-auto text-[#4F46E5] font-medium">{isExpanded ? 'Hide Changes' : 'View Changes'}</span>
                          </div>
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="px-12 pb-5 pt-2 grid grid-cols-1 md:grid-cols-2 gap-6 bg-[#F9FAFB] border-t border-[#E5E7EB]">
                          {log.before_state && Object.keys(log.before_state).length > 0 && (
                            <div>
                              <p className="text-xs font-bold text-red-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                Previous State
                              </p>
                              <pre className="text-[11px] leading-relaxed bg-white text-gray-800 rounded-lg p-3 overflow-auto max-h-60 border border-red-100 shadow-sm">
                                {JSON.stringify(log.before_state, null, 2)}
                              </pre>
                            </div>
                          )}
                          {log.after_state && Object.keys(log.after_state).length > 0 && (
                            <div className={!log.before_state || Object.keys(log.before_state).length === 0 ? "md:col-span-2" : ""}>
                              <p className="text-xs font-bold text-green-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                New State
                              </p>
                              <pre className="text-[11px] leading-relaxed bg-white text-gray-800 rounded-lg p-3 overflow-auto max-h-60 border border-green-100 shadow-sm">
                                {JSON.stringify(log.after_state, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {totalPages > 1 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-4">
              <p className="text-sm text-[#6B7280]">Showing page <span className="font-medium text-[#111827]">{page}</span> of <span className="font-medium text-[#111827]">{totalPages}</span></p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p: number) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-lg border border-[#E5E7EB] bg-white hover:bg-[#F3F5F9] disabled:opacity-50 transition-all shadow-sm"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setPage((p: number) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-2 rounded-lg border border-[#E5E7EB] bg-white hover:bg-[#F3F5F9] disabled:opacity-50 transition-all shadow-sm"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}