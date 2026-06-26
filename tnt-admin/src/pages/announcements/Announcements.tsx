import React, { useEffect, useState } from 'react';
import { Megaphone, Send, Clock, Users, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import { formatTimeAgo } from '../../utils/format';

interface Broadcast {
  id: number;
  title: string;
  message: string;
  severity: string;
  audience: string;
  sent_count: number;
  created_at: string;
}

const MAX_CHARS = 500;

type Severity = 'info' | 'warning' | 'critical';
type Audience = 'all' | 'faculty' | 'vendor_customers';

const SEVERITY_OPTIONS: { value: Severity; label: string; icon: React.ReactNode; color: string }[] = [
  { value: 'info', label: 'Info', icon: <Info className="w-4 h-4" />, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  { value: 'warning', label: 'Warning', icon: <AlertTriangle className="w-4 h-4" />, color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
  { value: 'critical', label: 'Critical', icon: <AlertCircle className="w-4 h-4" />, color: 'text-red-400 bg-red-500/10 border-red-500/20' },
];

const AUDIENCE_OPTIONS: { value: Audience; label: string; desc: string }[] = [
  { value: 'all', label: 'All Users', desc: 'Every active user on TNT' },
  { value: 'faculty', label: 'Faculty Only', desc: 'Users with faculty role' },
  { value: 'vendor_customers', label: "Vendor's Customers", desc: 'Customers of a specific vendor' },
];

export default function Announcements() {
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [severity, setSeverity] = useState<Severity>('info');
  const [audience, setAudience] = useState<Audience>('all');
  const [vendorId, setVendorId] = useState<string>('');
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);

  // Fetch real broadcast history on mount
  useEffect(() => {
    setLoadingHistory(true);
    adminApi
      .getBroadcasts({ limit: 50 })
      .then((res) => {
        setBroadcasts(res.data.broadcasts ?? []);
      })
      .catch(() => {
        toast.error('Failed to load broadcast history');
      })
      .finally(() => setLoadingHistory(false));
  }, []);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      toast.error('Please enter a title');
      return;
    }
    if (!message.trim()) {
      toast.error('Please enter a message');
      return;
    }
    if (audience === 'vendor_customers' && !vendorId.trim()) {
      toast.error('Please enter a vendor ID');
      return;
    }

    setSending(true);
    try {
      const res = await adminApi.sendBroadcast({
        title: title.trim(),
        message: message.trim(),
        severity,
        audience,
        vendor_id: audience === 'vendor_customers' ? parseInt(vendorId, 10) : null,
      });
      // Prepend the new broadcast to local list
      const newBroadcast: Broadcast = {
        id: res.data.broadcast_id,
        title: title.trim(),
        message: message.trim(),
        severity,
        audience,
        sent_count: res.data.sent_count ?? 0,
        created_at: new Date().toISOString(),
      };
      setBroadcasts((prev) => [newBroadcast, ...prev]);
      setTitle('');
      setMessage('');
      setSeverity('info');
      setAudience('all');
      setVendorId('');
      toast.success(`📢 Broadcast sent to ${res.data.sent_count} recipient(s)`);
    } catch {
      toast.error('Failed to send broadcast');
    } finally {
      setSending(false);
    }
  };

  const remaining = MAX_CHARS - message.length;
  return (
    <div className="max-w-3xl space-y-6">
      {/* Compose */}
      <div className="tnt-card">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-lg bg-[#E85D24]/20 flex items-center justify-center">
            <Megaphone className="w-5 h-5 text-[#E85D24]" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-[#111827]">Broadcast Announcement</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <Users className="w-3.5 h-3.5 text-[#6B7280]" />
              <span className="text-xs text-[#6B7280]">
                Push notification to mobile users; critical severity also sends SMS
              </span>
            </div>
          </div>
        </div>

        <form onSubmit={handleSend} className="space-y-4">
          {/* Severity selector */}
          <div>
            <label className="tnt-label">Severity</label>
            <div className="flex gap-2">
              {SEVERITY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setSeverity(opt.value)}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                    severity === opt.value
                      ? opt.color
                      : 'border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB]'
                  }`}
                >
                  {opt.icon}
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Audience filter */}
          <div>
            <label className="tnt-label">Target Audience</label>
            <div className="flex flex-wrap gap-2">
              {AUDIENCE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setAudience(opt.value)}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                    audience === opt.value
                      ? 'bg-[#E85D24]/10 border-[#E85D24]/30 text-[#E85D24]'
                      : 'border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB]'
                  }`}
                >
                  <Users className="w-3.5 h-3.5" />
                  {opt.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-[#6B7280] mt-1">
              {AUDIENCE_OPTIONS.find((o) => o.value === audience)?.desc}
            </p>
          </div>

          {/* Vendor ID (shown only for vendor_customers) */}
          {audience === 'vendor_customers' && (
            <div>
              <label className="tnt-label">Vendor ID</label>
              <input
                type="number"
                value={vendorId}
                onChange={(e) => setVendorId(e.target.value)}
                placeholder="Enter vendor user ID"
                className="tnt-input"
                min={1}
                required
              />
            </div>
          )}

          <div>
            <label className="tnt-label">Announcement Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Canteen A Closed Tomorrow"
              className="tnt-input"
              maxLength={100}
              required
            />
          </div>

          <div>
            <label className="tnt-label">Message</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value.slice(0, MAX_CHARS))}
              placeholder="Type your announcement message here..."
              rows={5}
              className="tnt-input resize-none"
              required
            />
            <div className="flex items-center justify-between mt-1.5">
              <div className="flex items-center gap-1.5">
                {remaining < 50 ? (
                  <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                ) : (
                  <CheckCircle className="w-3.5 h-3.5 text-green-400/50" />
                )}
                <span
                  className={`text-xs ${remaining < 50 ? 'text-amber-400' : 'text-[#6B7280]'}`}
                >
                  {remaining} characters remaining
                </span>
              </div>
              <div className="w-24 h-1 bg-[#E5E7EB] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    remaining < 50
                      ? 'bg-amber-400'
                      : remaining < 150
                      ? 'bg-[#E85D24]'
                      : 'bg-green-400'
                  }`}
                  style={{ width: `${((MAX_CHARS - remaining) / MAX_CHARS) * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* Severity-specific warning */}
          {severity === 'critical' && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 flex gap-2 text-xs text-red-400">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                <strong>Critical</strong> — This will send an SMS message to <strong>every</strong>{' '}
                recipient in addition to a push notification. Use only for urgent campus-wide issues.
              </span>
            </div>
          )}
          {severity === 'info' && (
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 flex gap-2 text-xs text-blue-400">
              <Info className="w-4 h-4 shrink-0 mt-0.5" />
              <span>Push notification only. No SMS sent for info severity.</span>
            </div>
          )}

          <button
            type="submit"
            disabled={sending || !title.trim() || !message.trim()}
            className="btn-primary"
          >
            {sending ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Send Broadcast
              </>
            )}
          </button>
        </form>
      </div>

      {/* Broadcast History */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-4 h-4 text-[#6B7280]" />
          <h3 className="text-sm font-semibold text-[#111827]">Broadcast History</h3>
          <span className="badge bg-[#F3F5F9] text-[#6B7280] border-[#E5E7EB]">
            {broadcasts.length}
          </span>
        </div>

        <div className="space-y-3">
          {loadingHistory ? (
            <div className="tnt-card text-center py-10 text-[#6B7280] text-sm">
              <div className="w-5 h-5 border-2 border-[#E85D24]/30 border-t-[#E85D24] rounded-full animate-spin mx-auto mb-2" />
              Loading...
            </div>
          ) : broadcasts.length === 0 ? (
            <div className="tnt-card text-center py-10 text-[#6B7280] text-sm">
              No broadcasts sent yet
            </div>
          ) : (
            broadcasts.map((bc) => {
              const sev = SEVERITY_OPTIONS.find((s) => s.value === bc.severity) ?? SEVERITY_OPTIONS[0];
              return (
                <div key={bc.id} className="tnt-card transition-all">
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                        bc.severity === 'critical'
                          ? 'bg-red-500/10 text-red-400'
                          : bc.severity === 'warning'
                          ? 'bg-amber-500/10 text-amber-400'
                          : 'bg-blue-500/10 text-blue-400'
                      }`}
                    >
                      {sev.icon}
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="text-sm font-semibold text-[#111827]">{bc.title}</h4>
                          <span
                            className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full uppercase ${
                              bc.severity === 'critical'
                                ? 'bg-red-500/10 text-red-400'
                                : bc.severity === 'warning'
                                ? 'bg-amber-500/10 text-amber-400'
                                : 'bg-blue-500/10 text-blue-400'
                            }`}
                          >
                            {bc.severity}
                          </span>
                          <span className="text-[10px] text-[#6B7280] bg-[#F3F5F9] px-1.5 py-0.5 rounded-full">
                            {bc.audience === 'all' ? 'All' : bc.audience === 'faculty' ? 'Faculty' : 'Vendor'}
                          </span>
                        </div>
                        <span className="text-xs text-[#6B7280] shrink-0 font-mono">
                          {formatTimeAgo(bc.created_at)}
                        </span>
                      </div>
                      <p className="text-xs text-[#4B5563] mt-1 leading-relaxed">{bc.message}</p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <Users className="w-3 h-3 text-[#6B7280]" />
                        <span className="text-[10px] text-[#6B7280]">
                          Delivered to <strong>{bc.sent_count}</strong> recipient(s)
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
