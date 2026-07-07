import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, GraduationCap, CalendarDays, Save, Plus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import type { FacultyPriorityPolicy } from '../../types';

export default function FacultyPolicy() {
  const navigate = useNavigate();
  const location = useLocation();

  const [policy, setPolicy] = useState<FacultyPriorityPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    timeWindows: [{ start: '08:00', end: '09:30', priority_weight: 2 }],
    discountPercent: 10,
    isActive: true,
  });

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getFacultyPolicy();
      if (res.data) {
        const p = res.data;
        setPolicy(p);
        setForm({
          timeWindows: p.time_windows || [{ start: '08:00', end: '09:30', priority_weight: 2 }],
          discountPercent: p.discount_percent || 10,
          isActive: p.is_active,
        });
      }
    } catch { /* silent — use defaults */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: FacultyPriorityPolicy = {
        time_windows: form.timeWindows,
        discount_percent: form.discountPercent,
        is_active: form.isActive,
      };
      await adminApi.setFacultyPolicy(payload);
      toast.success('Faculty priority policy updated — live in mobile app');
    } catch { toast.error('Failed to update policy'); }
    finally { setSaving(false); }
  };

  const addWindow = () => setForm(f => ({
    ...f,
    timeWindows: [...f.timeWindows, { start: '12:00', end: '13:00', priority_weight: 1.5 }]
  }));

  const removeWindow = (idx: number) => setForm(f => ({
    ...f, timeWindows: f.timeWindows.filter((_, i) => i !== idx)
  }));

  return (
    <div className="space-y-5">
      {/* Sub-nav */}
          <div className="flex items-center gap-1 p-1 bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl w-fit">
        <button
          className={`tab-btn ${location.pathname === '/policies' ? 'active' : ''}`}
          onClick={() => navigate('/policies')}
        >
          <GraduationCap className="w-3.5 h-3.5" /> Faculty Priority
        </button>
        <button
          className={`tab-btn ${location.pathname.includes('university') ? 'active' : ''}`}
          onClick={() => navigate('/policies/university')}
        >
          <Shield className="w-3.5 h-3.5" /> University Policy
        </button>
        <button
          className={`tab-btn ${location.pathname.includes('calendar') ? 'active' : ''}`}
          onClick={() => navigate('/policies/calendar')}
        >
          <CalendarDays className="w-3.5 h-3.5" /> Calendar
        </button>
      </div>

      <div className="tnt-card">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-[#111827]">Faculty Priority Policy</h3>
            <p className="text-xs text-[#6B7280]">
              Faculty members get priority booking during defined time windows
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${form.isActive ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
            <span className="text-xs text-[#6B7280]">{form.isActive ? 'Active' : 'Inactive'}</span>
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => <div key={i} className="skeleton h-12 rounded-lg" />)}
          </div>
        ) : (
          <div className="space-y-5">
            {/* Active toggle */}
            <div className="flex items-center gap-3 p-4 bg-[#F3F5F9] rounded-lg">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.isActive}
                  onChange={e => setForm(f => ({ ...f, isActive: e.target.checked }))}
                  className="sr-only peer"
                />
                <div className="w-10 h-6 bg-[#D1D5DB] peer-checked:bg-[#E85D24] rounded-full transition-colors" />
                <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
              </label>
              <div>
                <p className="text-sm font-medium text-[#111827]">Enable Faculty Priority</p>
                <p className="text-xs text-[#6B7280]">Faculty will get priority slot access during set windows</p>
              </div>
            </div>

            {/* Discount */}
            <div className="max-w-xs">
              <label className="tnt-label">Faculty Discount %</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={50}
                  value={form.discountPercent}
                  onChange={e => setForm(f => ({ ...f, discountPercent: Number(e.target.value) }))}
                  className="flex-1 accent-[#E85D24]"
                />
                <span className="w-12 text-center font-mono font-bold text-[#E85D24] text-lg">
                  {form.discountPercent}%
                </span>
              </div>
              <p className="text-xs text-[#6B7280] mt-1">
                Faculty get {form.discountPercent}% discount on orders during priority windows
              </p>
            </div>

            {/* Time Windows */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="tnt-label mb-0">Priority Time Windows</label>
                <button onClick={addWindow} className="btn-ghost btn-sm">
                  <Plus className="w-3.5 h-3.5" /> Add Window
                </button>
              </div>
              <div className="space-y-3">
                {form.timeWindows.map((w, idx) => (
                  <div key={idx} className="flex flex-wrap items-center gap-3 p-3 bg-[#F3F5F9] rounded-lg border border-[#E5E7EB]">
                    <div className="flex items-center gap-2">
                      <input
                        type="time"
                        value={w.start}
                        onChange={e => setForm(f => ({
                          ...f,
                          timeWindows: f.timeWindows.map((tw, i) => i === idx ? { ...tw, start: e.target.value } : tw)
                        }))}
                        className="tnt-input w-28 text-sm"
                      />
                      <span className="text-[#6B7280] text-sm">to</span>
                      <input
                        type="time"
                        value={w.end}
                        onChange={e => setForm(f => ({
                          ...f,
                          timeWindows: f.timeWindows.map((tw, i) => i === idx ? { ...tw, end: e.target.value } : tw)
                        }))}
                        className="tnt-input w-28 text-sm"
                      />
                    </div>
                    <div className="flex items-center gap-2 flex-1">
                      <label className="text-xs text-[#6B7280] whitespace-nowrap">Priority Weight:</label>
                      <input
                        type="number"
                        value={w.priority_weight}
                        onChange={e => setForm(f => ({
                          ...f,
                          timeWindows: f.timeWindows.map((tw, i) => i === idx ? { ...tw, priority_weight: Number(e.target.value) } : tw)
                        }))}
                        min={1}
                        max={10}
                        step={0.5}
                        className="tnt-input w-20 text-sm"
                      />
                    </div>
                    {form.timeWindows.length > 1 && (
                      <button onClick={() => removeWindow(idx)} className="text-red-400 hover:text-red-300 ml-auto">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Info box */}
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4 text-xs text-purple-300">
              <p className="font-medium mb-1">📌 How this works</p>
              <p>During priority windows, faculty users are moved to the front of the booking queue. A higher priority weight means more preference over regular student bookings.</p>
            </div>

            <button onClick={handleSave} disabled={saving} className="btn-primary">
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Faculty Policy'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
