import React, { useState, useEffect } from 'react';
import { Shield, Search, ChevronLeft, ChevronRight, Clock, User, Package, Tag, FileText, Megaphone, LogIn } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import { cn } from '../../utils/cn';

interface AuditLogEntry {
  id: number;
  actor_id: number | null;
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
  { value: 'policy', label: 'Policies', icon: Shield },
  { value: 'voucher', label: 'Vouchers', icon: Tag },
  { value: 'announcement', label: 'Announcements', icon: Megaphone },
];

const CATEGORY_STYLES: Record<string, string> = {
  auth: 'bg-blue-50 text-blue-700 border-blue-200',
  user: 'bg-purple-50 text-purple-700 border-purple-200',
  vendor: 'bg-amber-50 text-amber-700 border-amber-200',
  order: 'bg-green-50 text-green-700 border-green-200',
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
  const [logs, setLogs] = useState([] as AuditLogEntry[]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [category, setCategory] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [expandedRow, setExpandedRow] = useState(null as number | null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [category, dateFrom, dateTo]);

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      try {
        const params: any = { page, page_size: 50 };
        if (debouncedSearch) params.search = debouncedSearch;
        if (category) params.action_category = category;
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
    fetchLogs();
  }, [page, debouncedSearch, category, dateFrom, dateTo]);

  const formatTimestamp = (iso: string) => {
    const d = new Date(iso);
    return {
      date: d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }),
      time: d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }),
    };
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Shield className="h-6 w-6 text-[#4F46E5]" />
        <div>
          <h2 className="text-2xl font-bold text-[#111827]">Audit Logs</h2>
          <p className="text-sm text-[#6B7280]">Immutable record of all admin actions</p>
        </div>
      </div>

      <div className="tnt-card flex flex-wrap gap-3 items-end">
        <div className="relative min-w-[200px] flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
          <input
            type="text"
            placeholder="Search by action..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="tnt-input pl-9"
          />
        </div>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="tnt-select">
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
        <div className="flex items-center gap-2 text-sm text-[#6B7280]">
          <span>From</span>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="tnt-input py-2" />
          <span>To</span>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="tnt-input py-2" />
        </div>
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
                        <span className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border', catStyle)}>
                          {log.action_category}
                        </span>
                        <span className="text-sm font-semibold text-[#111827]">{humanizeAction(log.action)}</span>
                        {log.entity_type && log.entity_id && (
                          <span className="text-xs text-[#9CA3AF]">{log.entity_type} #{log.entity_id}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-xs text-[#9CA3AF]">
                        <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{date} · {time}</span>
                        {log.actor_id && <span className="flex items-center gap-1"><User className="h-3 w-3" />Actor #{log.actor_id}{log.actor_role && ` (${log.actor_role})`}</span>}
                        {log.ip_address && <span>{log.ip_address}</span>}
                        <span className="ml-auto text-[#4F46E5]">{isExpanded ? '▲ Hide details' : '▼ Show details'}</span>
                      </div>
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="px-12 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {log.before_state && (
                        <div>
                          <p className="text-xs font-semibold text-[#9CA3AF] mb-1">BEFORE</p>
                          <pre className="text-xs bg-red-50 text-red-800 rounded-lg p-3 overflow-auto max-h-40 border border-red-100">
                            {JSON.stringify(log.before_state, null, 2)}
                          </pre>
                        </div>
                      )}
                      {log.after_state && (
                        <div>
                          <p className="text-xs font-semibold text-[#9CA3AF] mb-1">AFTER</p>
                          <pre className="text-xs bg-green-50 text-green-800 rounded-lg p-3 overflow-auto max-h-40 border border-green-100">
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
        <div className="flex items-center justify-between">
          <p className="text-sm text-[#6B7280]">Page {page} of {totalPages}</p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p: number) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg border border-[#E5E7EB] hover:bg-[#F3F5F9] disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p: number) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 rounded-lg border border-[#E5E7EB] hover:bg-[#F3F5F9] disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}