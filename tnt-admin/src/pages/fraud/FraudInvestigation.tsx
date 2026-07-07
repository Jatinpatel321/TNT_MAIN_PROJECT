import React, { useState, useEffect, useCallback } from 'react';
import { 
  Search, Terminal, ShieldAlert, Siren, Fingerprint, 
  MapPin, Ban, User, RefreshCw, Eye, ArrowRight, ClipboardList 
} from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import { formatDate } from '../../utils/format';

interface AuditLogEntry {
  id: number;
  actor_id: number | null;
  actor_role: string | null;
  action: string;
  action_category: string;
  entity_type: string | null;
  entity_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  metadata?: any;
}

export default function FraudInvestigation() {
  const [ipQuery, setIpQuery] = useState('');
  const [phonePrefixQuery, setPhonePrefixQuery] = useState('');
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [searching, setSearching] = useState(false);
  const [totalLogs, setTotalLogs] = useState(0);

  // Active scan queries
  const [sharedIpUsers, setSharedIpUsers] = useState<any[]>([]);
  const [sequentialPhones, setSequentialPhones] = useState<any[]>([]);

  const fetchFailedLogins = useCallback(async () => {
    setSearching(true);
    try {
      const res = await adminApi.getAuditLogs({
        page: 1,
        page_size: 30,
        action_category: 'auth',
      });
      setLogs(res.data.logs || []);
      setTotalLogs(res.data.total || 0);
    } catch {
      toast.error('Failed to load login audit logs');
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    fetchFailedLogins();
  }, [fetchFailedLogins]);

  const handleIpSearch = async () => {
    if (!ipQuery.trim()) {
      toast.error('Please enter an IP address');
      return;
    }
    setSearching(true);
    try {
      const res = await adminApi.getAuditLogs({
        page: 1,
        page_size: 50,
        search: ipQuery,
      });
      const ipLogs = res.data.logs || [];
      setLogs(ipLogs);
      setTotalLogs(res.data.total || 0);

      // Extract unique user ids that logged in from this IP
      const users: Record<string, any> = {};
      ipLogs.forEach((log: any) => {
        if (log.actor_id) {
          users[log.actor_id] = {
            id: log.actor_id,
            role: log.actor_role,
            last_login: log.created_at,
            ua: log.user_agent,
          };
        }
      });
      setSharedIpUsers(Object.values(users));
      toast.success(`Found ${ipLogs.length} events matching IP ${ipQuery}`);
    } catch {
      toast.error('Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleSequentialPhoneSearch = async () => {
    if (!phonePrefixQuery.trim()) {
      toast.error('Please enter a phone prefix (at least 6 digits)');
      return;
    }
    setSearching(true);
    try {
      const res = await adminApi.getAuditLogs({
        page: 1,
        page_size: 50,
        search: phonePrefixQuery,
      });
      setLogs(res.data.logs || []);
      setTotalLogs(res.data.total || 0);
      toast.success(`Queried audit logs matching phone search`);
    } catch {
      toast.error('Search failed');
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold text-[#111827]">Investigation Workspace</h1>
        <p className="text-sm text-[#4B5563]">Drill down into audit logs, IP networks, and credential anomalies</p>
      </div>

      {/* Query Console Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* IP sharing search */}
        <div className="tnt-card space-y-4">
          <h3 className="text-sm font-semibold text-[#111827] flex items-center gap-2">
            <MapPin className="w-5 h-5 text-[#6B7280]" />
            IP Address Analyzer
          </h3>
          <p className="text-xs text-[#6B7280]">Query login logs and user account overlap for a specific IP address subnet.</p>
          <div className="flex gap-2">
            <input
              type="text"
              value={ipQuery}
              onChange={(e) => setIpQuery(e.target.value)}
              placeholder="e.g. 192.168.1.50"
              className="flex-1 text-xs border border-[#E5E7EB] bg-white rounded-xl px-4 py-2 outline-none text-[#111827]"
            />
            <button
              onClick={handleIpSearch}
              className="btn-primary"
            >
              Analyze
            </button>
          </div>
          {sharedIpUsers.length > 0 && (
            <div className="pt-4 border-t border-[#E5E7EB] space-y-2">
              <p className="text-xs font-semibold text-[#111827]">Distinct Accounts Logging from IP:</p>
              <div className="divide-y divide-[#E5E7EB]">
                {sharedIpUsers.map((u) => (
                  <div key={u.id} className="py-2 flex justify-between items-center text-xs">
                    <div>
                      <span className="font-semibold text-[#111827]">User ID #{u.id}</span>
                      <span className="ml-2 inline-flex px-1.5 py-0.5 rounded bg-slate-100 text-[#4B5563] text-[9px] uppercase">
                        {u.role}
                      </span>
                    </div>
                    <span className="text-[#6B7280]">{formatDate(u.last_login)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sequential phone lookup */}
        <div className="tnt-card space-y-4">
          <h3 className="text-sm font-semibold text-[#111827] flex items-center gap-2">
            <Fingerprint className="w-5 h-5 text-[#6B7280]" />
            Sequential Number Pattern Finder
          </h3>
          <p className="text-xs text-[#6B7280]">Search for registration clusters by entering a common phone prefix (e.g. +91930000).</p>
          <div className="flex gap-2">
            <input
              type="text"
              value={phonePrefixQuery}
              onChange={(e) => setPhonePrefixQuery(e.target.value)}
              placeholder="e.g. +919300"
              className="flex-1 text-xs border border-[#E5E7EB] bg-white rounded-xl px-4 py-2 outline-none text-[#111827]"
            />
            <button
              onClick={handleSequentialPhoneSearch}
              className="btn-primary"
            >
              Find Pattern
            </button>
          </div>
        </div>
      </div>

      {/* Audit Logs Board */}
      <div className="tnt-card space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-sm font-semibold text-[#111827] flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-[#6B7280]" />
            Authentication Audit Log ({totalLogs} events)
          </h3>
          <button
            onClick={fetchFailedLogins}
            className="p-1.5 border border-[#E5E7EB] bg-white hover:bg-[#F3F5F9] rounded-lg transition-all"
            title="Refresh logs feed"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#4B5563] ${searching ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {searching ? (
          <div className="py-20 text-center text-[#6B7280]">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-[#4F46E5] mb-2" />
            <p className="text-xs">Fetching audit logs...</p>
          </div>
        ) : logs.length > 0 ? (
          <div className="overflow-x-auto -mx-6">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#F8FAFC] border-y border-[#E5E7EB] text-xs font-semibold text-[#4B5563]">
                  <th className="px-6 py-3">Logged Date</th>
                  <th className="px-6 py-3">Action</th>
                  <th className="px-6 py-3">Target Entity</th>
                  <th className="px-6 py-3">IP Address</th>
                  <th className="px-6 py-3">User Agent</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E7EB]">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-[#F3F5F9] text-xs text-[#111827] transition-colors">
                    <td className="px-6 py-4 text-[#6B7280]">
                      {formatDate(log.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                        log.action === 'auth.login_failed' ? 'bg-red-50 text-red-700 border-red-200' :
                        log.action === 'auth.login_success' ? 'bg-green-50 text-green-700 border-green-200' :
                        'bg-slate-50 text-slate-600 border-slate-200'
                      }`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono font-medium text-[#4B5563]">
                      {log.entity_type && log.entity_id ? `${log.entity_type} (#${log.entity_id})` : 'System'}
                    </td>
                    <td className="px-6 py-4 text-slate-700">
                      {log.ip_address || 'Unknown'}
                    </td>
                    <td className="px-6 py-4 max-w-xs truncate text-[#6B7280]" title={log.user_agent || undefined}>
                      {log.user_agent || 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12 text-center text-xs text-[#9CA3AF]">
            No matching audit logs found.
          </div>
        )}
      </div>
    </div>
  );
}
