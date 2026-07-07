import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Gift, Clock, Plus, Trash2, Save, History } from 'lucide-react';
import { type ColumnDef } from '@tanstack/react-table';
import toast from 'react-hot-toast';
import { DataTable } from '../../components/ui/DataTable';
import { rewardsApi } from '../../api/rewards';
import { formatDateTime } from '../../utils/format';
import type { OffPeakPolicy, OffPeakAuditEntry } from '../../types';

export default function OffPeakPolicy() {
  const navigate = useNavigate();
  const location = useLocation();

  const [policy, setPolicy] = useState<OffPeakPolicy | null>(null);
  const [audit, setAudit] = useState<OffPeakAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    timeWindows: [{ start: '10:00', end: '11:30' }, { start: '14:00', end: '16:00' }],
    bonusPoints: 10,
    multiplier: 1.5,
    isActive: true,
  });

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const [policyRes, auditRes] = await Promise.allSettled([
        rewardsApi.getOffPeakPolicy(),
        rewardsApi.getOffPeakAudit(),
      ]);
      if (policyRes.status === 'fulfilled' && policyRes.value.data) {
        const p = policyRes.value.data;
        setPolicy(p);
        setForm({
          timeWindows: p.time_windows || [{ start: '10:00', end: '11:30' }],
          bonusPoints: p.bonus_points_per_order || 10,
          multiplier: p.multiplier || 1.5,
          isActive: p.is_active,
        });
      }
      if (auditRes.status === 'fulfilled') {
        setAudit(Array.isArray(auditRes.value.data) ? auditRes.value.data : []);
      }
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: Partial<OffPeakPolicy> = {
        time_windows: form.timeWindows,
        bonus_points_per_order: form.bonusPoints,
        multiplier: form.multiplier,
        is_active: form.isActive,
      };
      const res = await rewardsApi.setOffPeakPolicy(payload);
      setPolicy(res.data);
      setEditing(false);
      toast.success('Off-peak policy updated — changes live in mobile app');
      fetch(); // refresh audit log
    } catch { toast.error('Failed to update policy'); }
    finally { setSaving(false); }
  };

  const addWindow = () => setForm(f => ({
    ...f, timeWindows: [...f.timeWindows, { start: '09:00', end: '10:00' }]
  }));

  const removeWindow = (idx: number) => setForm(f => ({
    ...f, timeWindows: f.timeWindows.filter((_, i) => i !== idx)
  }));

  const auditColumns: ColumnDef<OffPeakAuditEntry, unknown>[] = [
    {
      accessorKey: 'changed_by',
      header: 'Changed By',
      cell: ({ row }) => <span className="text-[#111827] text-sm">{row.original.changed_by}</span>,
    },
    {
      accessorKey: 'changed_at',
      header: 'When',
      cell: ({ row }) => (
        <span className="text-xs font-mono text-[#6B7280]">{formatDateTime(row.original.changed_at)}</span>
      ),
    },
    {
      id: 'change_summary',
      header: 'Change',
      cell: ({ row }) => (
        <div className="text-xs text-[#6B7280]">
          <span>Points: </span>
          <span className="text-[#111827]">
            {(row.original.previous_policy as OffPeakPolicy)?.bonus_points_per_order || '?'}
            {' → '}
            {(row.original.new_policy as OffPeakPolicy)?.bonus_points_per_order || '?'}
          </span>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {/* Sub-nav */}
      <div className="flex items-center gap-1 p-1 bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl w-fit">
        <button
          className={`tab-btn ${location.pathname === '/rewards' ? 'active' : ''}`}
          onClick={() => navigate('/rewards')}
        >
          <Gift className="w-3.5 h-3.5" /> Vouchers
        </button>
        <button
          className={`tab-btn ${location.pathname.includes('off-peak') ? 'active' : ''}`}
          onClick={() => navigate('/rewards/off-peak')}
        >
          <Clock className="w-3.5 h-3.5" /> Off-Peak Policy
        </button>
      </div>

      {loading ? (
        <div className="space-y-4">
          <div className="skeleton h-48 rounded-xl" />
          <div className="skeleton h-64 rounded-xl" />
        </div>
      ) : (
        <>
          {/* Current Policy Card */}
          <div className="tnt-card">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-base font-semibold text-[#111827]">Off-Peak Bonus Policy</h3>
                <p className="text-xs text-[#6B7280] mt-0.5">
                  Students ordering during off-peak windows earn extra reward points
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${form.isActive ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
                <span className="text-xs text-[#6B7280]">{form.isActive ? 'Active' : 'Inactive'}</span>
                {!editing ? (
                  <button onClick={() => setEditing(true)} className="btn-ghost btn-sm ml-2">
                    Edit Policy
                  </button>
                ) : (
                  <button onClick={() => setEditing(false)} className="btn-ghost btn-sm ml-2 text-[#6B7280]">
                    Cancel
                  </button>
                )}
              </div>
            </div>

            {editing ? (
              <div className="space-y-4">
                {/* Active toggle */}
                <div className="flex items-center gap-3">
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.isActive}
                      onChange={e => setForm(f => ({ ...f, isActive: e.target.checked }))}
                      className="sr-only peer"
                    />
                    <div className="w-10 h-6 bg-[#D1D5DB] peer-checked:bg-[#E85D24] rounded-full transition-colors peer-focus:ring-2 peer-focus:ring-[#E85D24]" />
                    <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
                  </label>
                  <span className="text-sm text-[#6B7280]">Policy Active</span>
                </div>

                {/* Bonus points */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="tnt-label">Bonus Points per Order</label>
                    <input
                      type="number"
                      value={form.bonusPoints}
                      onChange={e => setForm(f => ({ ...f, bonusPoints: Number(e.target.value) }))}
                      className="tnt-input"
                      min={1}
                    />
                  </div>
                  <div>
                    <label className="tnt-label">Point Multiplier</label>
                    <input
                      type="number"
                      value={form.multiplier}
                      onChange={e => setForm(f => ({ ...f, multiplier: Number(e.target.value) }))}
                      className="tnt-input"
                      min={1}
                      max={5}
                      step={0.1}
                    />
                  </div>
                </div>

                {/* Time windows */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="tnt-label mb-0">Off-Peak Time Windows</label>
                    <button onClick={addWindow} className="btn-ghost btn-sm">
                      <Plus className="w-3.5 h-3.5" /> Add Window
                    </button>
                  </div>
                  <div className="space-y-2">
                    {form.timeWindows.map((w, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <input
                          type="time"
                          value={w.start}
                          onChange={e => setForm(f => ({
                            ...f,
                            timeWindows: f.timeWindows.map((tw, i) => i === idx ? { ...tw, start: e.target.value } : tw)
                          }))}
                          className="tnt-input w-32"
                        />
                        <span className="text-[#6B7280] text-sm">to</span>
                        <input
                          type="time"
                          value={w.end}
                          onChange={e => setForm(f => ({
                            ...f,
                            timeWindows: f.timeWindows.map((tw, i) => i === idx ? { ...tw, end: e.target.value } : tw)
                          }))}
                          className="tnt-input w-32"
                        />
                        {form.timeWindows.length > 1 && (
                          <button onClick={() => removeWindow(idx)} className="text-red-400 hover:text-red-300">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <button onClick={handleSave} disabled={saving} className="btn-primary">
                  <Save className="w-4 h-4" />
                  {saving ? 'Saving...' : 'Save Policy'}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#F3F5F9] rounded-lg p-4">
                    <p className="text-xs text-[#6B7280]">Bonus Points</p>
                    <p className="text-2xl font-bold text-[#E85D24] font-mono">{form.bonusPoints}</p>
                    <p className="text-xs text-[#6B7280]">per qualifying order</p>
                  </div>
                  <div className="bg-[#F3F5F9] rounded-lg p-4">
                    <p className="text-xs text-[#6B7280]">Multiplier</p>
                    <p className="text-2xl font-bold text-[#E85D24] font-mono">{form.multiplier}×</p>
                    <p className="text-xs text-[#6B7280]">point multiplier</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-[#6B7280] mb-2">Active Time Windows</p>
                  <div className="flex flex-wrap gap-2">
                    {form.timeWindows.map((w, i) => (
                      <span key={i} className="badge bg-[#E85D24]/10 text-[#E85D24] border-[#E85D24]/20 font-mono text-xs">
                        <Clock className="w-3 h-3 mr-1" />
                        {w.start} – {w.end}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Audit Log */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <History className="w-4 h-4 text-[#E85D24]" />
              <h3 className="text-sm font-semibold text-[#111827]">Policy Change History</h3>
            </div>
            <DataTable
              data={audit}
              columns={auditColumns}
              emptyMessage="No policy changes recorded yet"
            />
          </div>
        </>
      )}
    </div>
  );
}
