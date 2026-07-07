import React, { useCallback, useEffect, useState } from 'react';
import { Wallet, RefreshCw, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import { formatPaise, formatDateTime, formatDate } from '../../utils/format';

type FinTab = 'settlements' | 'refunds';

interface Settlement {
  id: number;
  vendor_id: number;
  vendor_name: string;
  period_start: string | null;
  period_end: string | null;
  total_amount: number;
  net_amount: number;
  order_count: number;
  status: string;
  settled_at: string | null;
  created_at: string | null;
}

interface RefundRequest {
  id: number;
  order_id: number;
  user_id: number;
  user_name: string;
  amount: number;
  reason: string | null;
  status: string;
  decision_note: string | null;
  requested_at: string | null;
  decided_at: string | null;
}

function statusPill(status: string) {
  const map: Record<string, string> = {
    pending: 'bg-amber-50 text-amber-600 border-amber-200',
    processing: 'bg-blue-50 text-blue-600 border-blue-200',
    completed: 'bg-green-50 text-green-600 border-green-200',
    approved: 'bg-green-50 text-green-600 border-green-200',
    failed: 'bg-red-50 text-red-600 border-red-200',
    rejected: 'bg-red-50 text-red-600 border-red-200',
  };
  return map[status] || 'bg-gray-50 text-gray-600 border-gray-200';
}

export default function Finance() {
  const [tab, setTab] = useState<FinTab>('settlements');
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [refunds, setRefunds] = useState<RefundRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, r] = await Promise.allSettled([adminApi.getSettlements(), adminApi.getRefundRequests()]);
      if (s.status === 'fulfilled') setSettlements(Array.isArray(s.value.data) ? s.value.data : []);
      if (r.status === 'fulfilled') setRefunds(Array.isArray(r.value.data) ? r.value.data : []);
    } catch { toast.error('Failed to load finance data'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const approveSettlement = async (id: number) => {
    setBusyId(id);
    try {
      await adminApi.approveSettlement(id);
      toast.success('Settlement approved');
      await load();
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Failed'); }
    finally { setBusyId(null); }
  };

  const approveRefund = async (id: number) => {
    setBusyId(id);
    try {
      await adminApi.approveRefundRequest(id);
      toast.success('Refund approved');
      await load();
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Refund failed'); }
    finally { setBusyId(null); }
  };

  const rejectRefund = async (id: number) => {
    const note = window.prompt('Reason for rejecting this refund?') || '';
    if (note === null) return;
    setBusyId(id);
    try {
      await adminApi.rejectRefundRequest(id, note);
      toast.success('Refund rejected');
      await load();
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Failed'); }
    finally { setBusyId(null); }
  };

  const pendingSettlements = settlements.filter(s => s.status === 'pending' || s.status === 'processing').length;
  const pendingRefunds = refunds.filter(r => r.status === 'pending').length;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-1 p-1 bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl w-fit">
          <button onClick={() => setTab('settlements')} className={`tab-btn ${tab === 'settlements' ? 'active' : ''} flex items-center gap-2`}>
            <Wallet className="w-4 h-4" /> Settlements
            {pendingSettlements > 0 && <span className="px-2 py-0.5 rounded-full text-[10px] bg-amber-50 text-amber-600 border border-amber-200">{pendingSettlements}</span>}
          </button>
          <button onClick={() => setTab('refunds')} className={`tab-btn ${tab === 'refunds' ? 'active' : ''} flex items-center gap-2`}>
            <RefreshCw className="w-4 h-4" /> Refund Requests
            {pendingRefunds > 0 && <span className="px-2 py-0.5 rounded-full text-[10px] bg-amber-50 text-amber-600 border border-amber-200">{pendingRefunds}</span>}
          </button>
        </div>
        <button onClick={load} className="btn-ghost" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
      </div>

      {loading ? (
        <div className="skeleton h-96 rounded-xl" />
      ) : tab === 'settlements' ? (
        <div className="tnt-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-[#6B7280] border-b border-[#E5E7EB]">
                <th className="py-2 px-3">Vendor</th>
                <th className="py-2 px-3">Period</th>
                <th className="py-2 px-3">Orders</th>
                <th className="py-2 px-3">Net Amount</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Settled</th>
                <th className="py-2 px-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {settlements.length === 0 && (
                <tr><td colSpan={7} className="py-8 text-center text-[#9CA3AF]">No settlements</td></tr>
              )}
              {settlements.map(s => (
                <tr key={s.id} className="border-b border-[#F3F4F6]">
                  <td className="py-2 px-3 font-medium text-[#111827]">{s.vendor_name}</td>
                  <td className="py-2 px-3 text-[#6B7280] text-xs">
                    {s.period_start ? formatDate(s.period_start) : '—'} – {s.period_end ? formatDate(s.period_end) : '—'}
                  </td>
                  <td className="py-2 px-3 font-mono">{s.order_count}</td>
                  <td className="py-2 px-3 font-mono font-semibold">{formatPaise(Math.round((s.net_amount || 0) * 100))}</td>
                  <td className="py-2 px-3"><span className={`px-2 py-0.5 rounded-full text-xs border ${statusPill(s.status)}`}>{s.status}</span></td>
                  <td className="py-2 px-3 text-xs text-[#6B7280]">{s.settled_at ? formatDateTime(s.settled_at) : '—'}</td>
                  <td className="py-2 px-3">
                    {s.status !== 'completed' ? (
                      <button onClick={() => approveSettlement(s.id)} disabled={busyId === s.id} className="btn-success btn-sm">
                        {busyId === s.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />} Approve
                      </button>
                    ) : <span className="text-xs text-green-600">Done</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="tnt-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-[#6B7280] border-b border-[#E5E7EB]">
                <th className="py-2 px-3">Order</th>
                <th className="py-2 px-3">User</th>
                <th className="py-2 px-3">Amount</th>
                <th className="py-2 px-3">Reason</th>
                <th className="py-2 px-3">Timeline</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {refunds.length === 0 && (
                <tr><td colSpan={7} className="py-8 text-center text-[#9CA3AF]">No refund requests</td></tr>
              )}
              {refunds.map(r => (
                <tr key={r.id} className="border-b border-[#F3F4F6]">
                  <td className="py-2 px-3 font-mono text-xs">#{r.order_id}</td>
                  <td className="py-2 px-3">{r.user_name}</td>
                  <td className="py-2 px-3 font-mono font-semibold">{formatPaise(r.amount)}</td>
                  <td className="py-2 px-3 text-xs text-[#6B7280] max-w-[180px] truncate">{r.reason || '—'}</td>
                  <td className="py-2 px-3 text-[11px] text-[#6B7280]">
                    <div className="flex items-center gap-1"><Clock className="w-3 h-3" /> {r.requested_at ? formatDateTime(r.requested_at) : '—'}</div>
                    {r.decided_at && <div className="mt-0.5">Decided {formatDateTime(r.decided_at)}</div>}
                    {r.decision_note && <div className="mt-0.5 italic">“{r.decision_note}”</div>}
                  </td>
                  <td className="py-2 px-3"><span className={`px-2 py-0.5 rounded-full text-xs border ${statusPill(r.status)}`}>{r.status}</span></td>
                  <td className="py-2 px-3">
                    {r.status === 'pending' ? (
                      <div className="flex gap-1">
                        <button onClick={() => approveRefund(r.id)} disabled={busyId === r.id} className="btn-success btn-sm">
                          {busyId === r.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                        </button>
                        <button onClick={() => rejectRefund(r.id)} disabled={busyId === r.id} className="btn-danger btn-sm">
                          <XCircle className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : <span className="text-xs text-[#9CA3AF]">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
