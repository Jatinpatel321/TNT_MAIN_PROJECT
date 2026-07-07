import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import { adminApi } from '../../api/admin';
import { WS_BASE_URL } from '../../utils/constants';
import {
  Shield, ShieldAlert, KeyRound, Users, AlertTriangle, Activity,
  Lock, Unlock, RefreshCw, XCircle, Trash2, Ban, UserCheck, ShieldCheck, Clock
} from 'lucide-react';
import toast from 'react-hot-toast';

interface SecurityMetric {
  active_sessions: number;
  failed_logins: number;
  fraud_alerts: number;
  critical_events: number;
  role_changes: number;
  permission_changes: number;
  api_abuse: number;
  rate_limit_violations: number;
  jwt_failures: number;
}

interface SecurityEvent {
  id: string;
  timestamp: number;
  event_type: string;
  severity: string;
  details: {
    token_preview?: string;
    reason?: string;
    path?: string;
    limit_key?: string;
    target?: string;
    duration?: number;
  };
  ip_address?: string;
  user_id?: number;
}

interface ActiveSession {
  token_key: string;
  user_id: number;
  role: string;
  phone: string;
  name: string;
  ttl: number;
}

export default function SecurityDashboard() {
  const { token } = useAuthStore();
  const [metrics, setMetrics] = useState<SecurityMetric | null>(null);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [blockedTargets, setBlockedTargets] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<'stream' | 'sessions' | 'blocks' | 'roles'>('stream');
  
  // Form states
  const [blockTarget, setBlockTarget] = useState('');
  const [blockReason, setBlockReason] = useState('');
  const [blockDuration, setBlockDuration] = useState(86400); // 1 day
  const [roleUserId, setRoleUserId] = useState('');
  const [newRole, setNewRole] = useState('student');
  const [loading, setLoading] = useState(false);

  // Fetch initial metrics
  const fetchMetrics = async () => {
    try {
      const res = await adminApi.getSecurityMetrics();
      setMetrics(res.data);
    } catch (err) {
      console.error('Error fetching metrics', err);
    }
  };

  // Fetch security events log
  const fetchEvents = async () => {
    try {
      const res = await adminApi.getSecurityEvents({ limit: 50 });
      setEvents(res.data);
    } catch (err) {
      console.error('Error fetching events', err);
    }
  };

  // Fetch active sessions
  const fetchSessions = async () => {
    try {
      const res = await adminApi.getActiveSessions();
      setSessions(res.data);
    } catch (err) {
      console.error('Error fetching active sessions', err);
    }
  };

  // Fetch blocked targets
  const fetchBlocks = async () => {
    try {
      const res = await adminApi.getBlockedTargets();
      setBlockedTargets(res.data);
    } catch (err) {
      console.error('Error fetching blocked targets', err);
    }
  };

  const handleRefreshAll = async () => {
    setLoading(true);
    await Promise.all([fetchMetrics(), fetchEvents(), fetchSessions(), fetchBlocks()]);
    setLoading(false);
    toast.success('Security data refreshed');
  };

  useEffect(() => {
    fetchMetrics();
    fetchEvents();
    fetchSessions();
    fetchBlocks();
  }, []);

  // WebSocket real-time connection
  useEffect(() => {
    if (!token) return;

    const socketUrl = `${WS_BASE_URL}/v1/admin/security/ws`;
    const socket = new WebSocket(socketUrl);

    socket.onopen = () => {
      socket.send(JSON.stringify({ token }));
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.authenticated) {
          console.log('Security WebSocket authenticated.');
          return;
        }

        // Prepend event to the stream
        setEvents((prev) => [data, ...prev].slice(0, 100));
        
        // Dynamic stats increment
        setMetrics((prev) => {
          if (!prev) return null;
          const updated = { ...prev };
          updated.critical_events += 1;
          
          if (data.event_type === 'jwt_failure') updated.jwt_failures += 1;
          else if (data.event_type === 'rate_limit_violation') updated.rate_limit_violations += 1;
          else if (data.event_type === 'api_abuse') updated.api_abuse += 1;
          
          return updated;
        });

        // Trigger notifications for critical events
        if (data.severity === 'critical' || data.severity === 'high') {
          toast(`Security Alert: ${data.event_type.replace('_', ' ').toUpperCase()}`, {
            icon: '⚠️',
            style: {
              background: '#EF4444',
              color: '#ffffff',
            },
          });
        }
      } catch (err) {
        console.error('Error reading websocket security event', err);
      }
    };

    return () => {
      socket.close();
    };
  }, [token]);

  // Actions
  const handleRevokeSession = async (tokenKey: string) => {
    if (!confirm('Are you sure you want to terminate this user session?')) return;
    try {
      await adminApi.revokeSession(tokenKey);
      toast.success('Session terminated successfully');
      fetchSessions();
      fetchMetrics();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to revoke session');
    }
  };

  const handleBlockTarget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!blockTarget || !blockReason) {
      toast.error('Please enter target and reason');
      return;
    }
    try {
      await adminApi.blockTarget({
        target: blockTarget,
        reason: blockReason,
        duration_seconds: blockDuration,
      });
      toast.success(`Blocked ${blockTarget}`);
      setBlockTarget('');
      setBlockReason('');
      fetchBlocks();
      fetchMetrics();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to apply block');
    }
  };

  const handleUnblockTarget = async (target: string) => {
    try {
      await adminApi.unblockTarget(target);
      toast.success(`Unblocked ${target}`);
      fetchBlocks();
      fetchMetrics();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to lift block');
    }
  };

  const handleChangeRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roleUserId) {
      toast.error('Please enter a User ID');
      return;
    }
    try {
      await adminApi.changeUserRole(parseInt(roleUserId), newRole);
      toast.success(`Role updated to ${newRole}`);
      setRoleUserId('');
      fetchMetrics();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to change user role');
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800 animate-pulse">Critical</span>;
      case 'high':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-800">High</span>;
      case 'medium':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Medium</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Low</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#111827] flex items-center gap-2">
            <ShieldAlert className="w-7 h-7 text-[#EF4444]" />
            Security Operations Center (SOC)
          </h1>
          <p className="text-sm text-[#4B5563]">Real-time threat monitoring, access control, and active sessions.</p>
        </div>
        <button
          onClick={handleRefreshAll}
          disabled={loading}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Stats
        </button>
      </div>

      {/* Metrics Grid */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {/* Active Sessions */}
          <div className="tnt-card bg-white p-4 border border-[#E5E7EB] rounded-2xl flex items-center gap-4 hover:shadow-md transition-all">
            <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-[#6B7280] font-medium uppercase tracking-wider">Active Sessions</p>
              <h3 className="text-xl font-bold text-[#111827]">{metrics.active_sessions}</h3>
            </div>
          </div>

          {/* Failed Logins */}
          <div className="tnt-card bg-white p-4 border border-[#E5E7EB] rounded-2xl flex items-center gap-4 hover:shadow-md transition-all">
            <div className="p-3 bg-red-50 text-red-600 rounded-xl">
              <XCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-[#6B7280] font-medium uppercase tracking-wider">Failed Logins</p>
              <h3 className="text-xl font-bold text-[#111827]">{metrics.failed_logins}</h3>
            </div>
          </div>

          {/* Fraud Alerts */}
          <div className="tnt-card bg-white p-4 border border-[#E5E7EB] rounded-2xl flex items-center gap-4 hover:shadow-md transition-all">
            <div className="p-3 bg-orange-50 text-orange-600 rounded-xl">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-[#6B7280] font-medium uppercase tracking-wider">Fraud Alerts</p>
              <h3 className="text-xl font-bold text-[#111827]">{metrics.fraud_alerts}</h3>
            </div>
          </div>

          {/* Critical Events */}
          <div className="tnt-card bg-white p-4 border border-[#E5E7EB] rounded-2xl flex items-center gap-4 hover:shadow-md transition-all">
            <div className="p-3 bg-rose-50 text-rose-600 rounded-xl">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-[#6B7280] font-medium uppercase tracking-wider">Critical Events</p>
              <h3 className="text-xl font-bold text-[#111827]">{metrics.critical_events}</h3>
            </div>
          </div>

          {/* Rate Limit Violations */}
          <div className="tnt-card bg-white p-4 border border-[#E5E7EB] rounded-2xl flex items-center gap-4 hover:shadow-md transition-all">
            <div className="p-3 bg-purple-50 text-purple-600 rounded-xl">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-[#6B7280] font-medium uppercase tracking-wider">Rate Limits Hit</p>
              <h3 className="text-xl font-bold text-[#111827]">{metrics.rate_limit_violations}</h3>
            </div>
          </div>

          {/* API Abuse */}
          <div className="tnt-card bg-white p-4 border border-[#E5E7EB] rounded-2xl flex items-center gap-4 hover:shadow-md transition-all">
            <div className="p-3 bg-yellow-50 text-yellow-600 rounded-xl">
              <Lock className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-[#6B7280] font-medium uppercase tracking-wider">API Abuse</p>
              <h3 className="text-xl font-bold text-[#111827]">{metrics.api_abuse}</h3>
            </div>
          </div>

          {/* JWT Failures */}
          <div className="tnt-card bg-white p-4 border border-[#E5E7EB] rounded-2xl flex items-center gap-4 hover:shadow-md transition-all">
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
              <KeyRound className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-[#6B7280] font-medium uppercase tracking-wider">JWT Failures</p>
              <h3 className="text-xl font-bold text-[#111827]">{metrics.jwt_failures}</h3>
            </div>
          </div>

          {/* Role Changes */}
          <div className="tnt-card bg-white p-4 border border-[#E5E7EB] rounded-2xl flex items-center gap-4 hover:shadow-md transition-all">
            <div className="p-3 bg-teal-50 text-teal-600 rounded-xl">
              <UserCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-[#6B7280] font-medium uppercase tracking-wider">Role Changes</p>
              <h3 className="text-xl font-bold text-[#111827]">{metrics.role_changes}</h3>
            </div>
          </div>

          {/* Permission Changes */}
          <div className="tnt-card bg-white p-4 border border-[#E5E7EB] rounded-2xl flex items-center gap-4 hover:shadow-md transition-all">
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-[#6B7280] font-medium uppercase tracking-wider">Perm Changes</p>
              <h3 className="text-xl font-bold text-[#111827]">{metrics.permission_changes}</h3>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#E5E7EB]">
        <button
          onClick={() => setActiveTab('stream')}
          className={`px-4 py-2 font-medium text-sm border-b-2 -mb-[2px] transition-all ${
            activeTab === 'stream' ? 'border-[#EF4444] text-[#EF4444]' : 'border-transparent text-[#6B7280]'
          }`}
        >
          Real-time Event Stream
        </button>
        <button
          onClick={() => setActiveTab('sessions')}
          className={`px-4 py-2 font-medium text-sm border-b-2 -mb-[2px] transition-all ${
            activeTab === 'sessions' ? 'border-[#EF4444] text-[#EF4444]' : 'border-transparent text-[#6B7280]'
          }`}
        >
          Active Sessions ({sessions.length})
        </button>
        <button
          onClick={() => setActiveTab('blocks')}
          className={`px-4 py-2 font-medium text-sm border-b-2 -mb-[2px] transition-all ${
            activeTab === 'blocks' ? 'border-[#EF4444] text-[#EF4444]' : 'border-transparent text-[#6B7280]'
          }`}
        >
          Threat Controls (IP Blocks)
        </button>
        <button
          onClick={() => setActiveTab('roles')}
          className={`px-4 py-2 font-medium text-sm border-b-2 -mb-[2px] transition-all ${
            activeTab === 'roles' ? 'border-[#EF4444] text-[#EF4444]' : 'border-transparent text-[#6B7280]'
          }`}
        >
          Access Overrides
        </button>
      </div>

      {/* Tab Contents */}
      <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6">
        {/* Real-time Stream */}
        {activeTab === 'stream' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center mb-2">
              <h3 className="text-lg font-bold text-[#111827]">Live SOC Threat Stream</h3>
              <span className="flex items-center gap-1.5 text-xs text-green-500 font-semibold uppercase animate-pulse">
                <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
                Live Monitoring Connected
              </span>
            </div>
            {events.length === 0 ? (
              <div className="text-center py-12 text-[#6B7280]">
                No security events recorded. Monitoring active...
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-[#E5E7EB] text-[#6B7280] font-medium">
                      <th className="py-3 px-4">Timestamp</th>
                      <th className="py-3 px-4">Event</th>
                      <th className="py-3 px-4">Severity</th>
                      <th className="py-3 px-4">IP Address</th>
                      <th className="py-3 px-4">Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((evt) => (
                      <tr key={evt.id} className="border-b border-[#F3F4F6] hover:bg-[#F9FAFB] transition-colors">
                        <td className="py-3 px-4 font-mono text-xs text-[#6B7280]">
                          {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                        </td>
                        <td className="py-3 px-4 font-semibold text-[#111827] capitalize">
                          {evt.event_type.replace('_', ' ')}
                        </td>
                        <td className="py-3 px-4">{getSeverityBadge(evt.severity)}</td>
                        <td className="py-3 px-4 font-mono text-xs text-[#374151]">
                          {evt.ip_address || '-'}
                        </td>
                        <td className="py-3 px-4 text-xs text-[#4B5563] max-w-xs truncate" title={JSON.stringify(evt.details)}>
                          {evt.details.reason || evt.details.limit_key || `User #${evt.user_id}`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Active Sessions */}
        {activeTab === 'sessions' && (
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-[#111827] mb-2">Authenticated Login Sessions</h3>
            {sessions.length === 0 ? (
              <div className="text-center py-12 text-[#6B7280]">No active user sessions found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-[#E5E7EB] text-[#6B7280] font-medium">
                      <th className="py-3 px-4">User</th>
                      <th className="py-3 px-4">Phone</th>
                      <th className="py-3 px-4">Role</th>
                      <th className="py-3 px-4">Expires In</th>
                      <th className="py-3 px-4 text-right">Revocation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map((sess) => (
                      <tr key={sess.token_key} className="border-b border-[#F3F4F6] hover:bg-[#F9FAFB] transition-colors">
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-semibold text-[#111827]">{sess.name}</p>
                            <p className="text-xs text-[#6B7280]">ID: {sess.user_id}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4 font-mono text-xs text-[#374151]">{sess.phone}</td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 capitalize">
                            {sess.role}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-xs text-[#6B7280] flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          {Math.round(sess.ttl / 3600)}h {Math.round((sess.ttl % 3600) / 60)}m
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => handleRevokeSession(sess.token_key)}
                            className="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors"
                            title="Force Logout Session"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Threat Controls */}
        {activeTab === 'blocks' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Form */}
            <div className="lg:col-span-1 border-r border-[#E5E7EB] pr-6 space-y-4">
              <h3 className="text-lg font-bold text-[#111827] flex items-center gap-1.5">
                <Ban className="w-5 h-5 text-red-500" />
                Add Target Block
              </h3>
              <form onSubmit={handleBlockTarget} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-[#4B5563] mb-1">Target IP or Phone</label>
                  <input
                    type="text"
                    value={blockTarget}
                    onChange={(e) => setBlockTarget(e.target.value)}
                    placeholder="e.g. 192.168.1.1 or +919999999999"
                    className="w-full text-sm border border-[#E5E7EB] rounded-xl px-3 py-2 focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#4B5563] mb-1">Reason for block</label>
                  <input
                    type="text"
                    value={blockReason}
                    onChange={(e) => setBlockReason(e.target.value)}
                    placeholder="e.g. Credential stuffing, rate abuse"
                    className="w-full text-sm border border-[#E5E7EB] rounded-xl px-3 py-2 focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#4B5563] mb-1">Duration</label>
                  <select
                    value={blockDuration}
                    onChange={(e) => setBlockDuration(parseInt(e.target.value))}
                    className="w-full text-sm border border-[#E5E7EB] rounded-xl px-3 py-2 focus:ring-1 focus:ring-red-500 focus:border-red-500 outline-none"
                  >
                    <option value={3600}>1 Hour</option>
                    <option value={86400}>24 Hours</option>
                    <option value={604800}>7 Days</option>
                    <option value={2592000}>30 Days</option>
                  </select>
                </div>
                <button type="submit" className="btn-primary w-full bg-red-600 hover:bg-red-700 text-white font-semibold">
                  Block Target
                </button>
              </form>
            </div>

            {/* List */}
            <div className="lg:col-span-2 space-y-4">
              <h3 className="text-lg font-bold text-[#111827]">Active Blocks in Redis</h3>
              {Object.keys(blockedTargets).length === 0 ? (
                <div className="text-center py-12 text-[#6B7280]">No IP addresses or Phone numbers currently blocked.</div>
              ) : (
                <div className="space-y-2">
                  {Object.entries(blockedTargets).map(([target, reason]) => (
                    <div key={target} className="flex justify-between items-center p-3 bg-red-50 border border-red-100 rounded-xl">
                      <div>
                        <p className="font-mono text-sm font-semibold text-red-950">{target}</p>
                        <p className="text-xs text-red-800">Reason: {reason}</p>
                      </div>
                      <button
                        onClick={() => handleUnblockTarget(target)}
                        className="text-green-600 hover:text-green-800 p-1.5 rounded-lg hover:bg-green-50 transition-all flex items-center gap-1 text-xs font-semibold"
                      >
                        <Unlock className="w-4 h-4" />
                        Unblock
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Access Overrides */}
        {activeTab === 'roles' && (
          <div className="max-w-md mx-auto space-y-6 py-4">
            <div className="text-center">
              <Shield className="w-12 h-12 text-[#EF4444] mx-auto mb-2" />
              <h3 className="text-lg font-bold text-[#111827]">User Role Override Panel</h3>
              <p className="text-xs text-[#6B7280]">Update user system permissions directly. All role modifications are audited.</p>
            </div>
            <form onSubmit={handleChangeRole} className="space-y-4 border border-[#E5E7EB] rounded-2xl p-4">
              <div>
                <label className="block text-xs font-semibold text-[#4B5563] mb-1">User ID</label>
                <input
                  type="number"
                  value={roleUserId}
                  onChange={(e) => setRoleUserId(e.target.value)}
                  placeholder="Enter User Database ID"
                  className="w-full text-sm border border-[#E5E7EB] rounded-xl px-3 py-2 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#4B5563] mb-1">New System Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full text-sm border border-[#E5E7EB] rounded-xl px-3 py-2 outline-none"
                >
                  <option value="student">Student</option>
                  <option value="faculty">Faculty</option>
                  <option value="vendor">Vendor</option>
                  <option value="staff">Staff</option>
                  <option value="admin">Administrator</option>
                </select>
              </div>
              <button type="submit" className="btn-primary w-full bg-red-600 hover:bg-red-700 text-white font-semibold">
                Apply Role Change
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
