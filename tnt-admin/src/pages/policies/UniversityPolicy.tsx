import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, GraduationCap, CalendarDays, Save, Plus, Trash2, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import type { UniversityPolicy } from '../../types';

const DEFAULT_CATEGORIES = ['food', 'stationery', 'beverages', 'snacks', 'printing', 'binding'];

export default function UniversityPolicy() {
  const navigate = useNavigate();
  const location = useLocation();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    maxOrdersPerDay: 5,
    allowedCategories: ['food', 'stationery', 'beverages', 'snacks'],
    breakWindows: [{ start: '13:00', end: '14:00' }],
    isActive: true,
  });

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getUniversityPolicy();
      if (res.data) {
        const p = res.data;
        setForm({
          maxOrdersPerDay: p.max_orders_per_user_per_day || 5,
          allowedCategories: p.allowed_categories || ['food', 'stationery'],
          breakWindows: p.break_windows || [{ start: '13:00', end: '14:00' }],
          isActive: p.is_active,
        });
      }
    } catch { /* use defaults */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: UniversityPolicy = {
        max_orders_per_user_per_day: form.maxOrdersPerDay,
        allowed_categories: form.allowedCategories,
        break_windows: form.breakWindows,
        is_active: form.isActive,
      };
      await adminApi.setUniversityPolicy(payload);
      toast.success('University policy updated — live in mobile app');
    } catch { toast.error('Failed to update policy'); }
    finally { setSaving(false); }
  };

  const toggleCategory = (cat: string) => {
    setForm(f => ({
      ...f,
      allowedCategories: f.allowedCategories.includes(cat)
        ? f.allowedCategories.filter(c => c !== cat)
        : [...f.allowedCategories, cat]
    }));
  };

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
          <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-[#111827]">University-Wide Ordering Policy</h3>
            <p className="text-xs text-[#6B7280]">
              Controls what all students and faculty can order across the campus
            </p>
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map(i => <div key={i} className="skeleton h-14 rounded-lg" />)}
          </div>
        ) : (
          <div className="space-y-6">
            {/* Max orders per day */}
            <div>
              <label className="tnt-label">Max Orders Per User Per Day</label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={form.maxOrdersPerDay}
                  onChange={e => setForm(f => ({ ...f, maxOrdersPerDay: Number(e.target.value) }))}
                  className="flex-1 accent-[#E85D24]"
                />
                <div className="w-14 h-10 rounded-lg bg-[#E85D24]/20 border border-[#E85D24]/30 flex items-center justify-center">
                  <span className="font-mono font-bold text-[#E85D24] text-lg">{form.maxOrdersPerDay}</span>
                </div>
              </div>
              <p className="text-xs text-[#6B7280] mt-1">
                Each user can place at most {form.maxOrdersPerDay} orders per calendar day
              </p>
            </div>

            {/* Allowed categories */}
            <div>
              <label className="tnt-label">Allowed Order Categories</label>
              <div className="flex flex-wrap gap-2 mt-2">
                {DEFAULT_CATEGORIES.map(cat => (
                  <button
                    key={cat}
                    onClick={() => toggleCategory(cat)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-150 capitalize
                      ${form.allowedCategories.includes(cat)
                        ? 'bg-[#E85D24]/20 text-[#E85D24] border-[#E85D24]/40'
                        : 'bg-[#F3F5F9] text-[#6B7280] border-[#E5E7EB] hover:border-[#6B7280]/40'
                      }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
              <p className="text-xs text-[#6B7280] mt-2">
                {form.allowedCategories.length} of {DEFAULT_CATEGORIES.length} categories allowed
              </p>
            </div>

            {/* Break windows (no ordering allowed) */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <label className="tnt-label mb-0">No-Order Windows (Break Times)</label>
                  <p className="text-xs text-[#6B7280] mt-0.5">Ordering is disabled during these periods</p>
                </div>
                <button
                  onClick={() => setForm(f => ({
                    ...f, breakWindows: [...f.breakWindows, { start: '10:30', end: '11:00' }]
                  }))}
                  className="btn-ghost btn-sm"
                >
                  <Plus className="w-3.5 h-3.5" /> Add
                </button>
              </div>
              <div className="space-y-2">
                {form.breakWindows.map((w, idx) => (
                  <div key={idx} className="flex items-center gap-3">
                    <input
                      type="time"
                      value={w.start}
                      onChange={e => setForm(f => ({
                        ...f,
                        breakWindows: f.breakWindows.map((bw, i) => i === idx ? { ...bw, start: e.target.value } : bw)
                      }))}
                      className="tnt-input w-28 text-sm"
                    />
                    <span className="text-[#6B7280]">to</span>
                    <input
                      type="time"
                      value={w.end}
                      onChange={e => setForm(f => ({
                        ...f,
                        breakWindows: f.breakWindows.map((bw, i) => i === idx ? { ...bw, end: e.target.value } : bw)
                      }))}
                      className="tnt-input w-28 text-sm"
                    />
                    <button
                      onClick={() => setForm(f => ({ ...f, breakWindows: f.breakWindows.filter((_, i) => i !== idx) }))}
                      className="text-red-400 hover:text-red-300"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Info */}
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 flex gap-3 text-xs text-blue-300">
              <Info className="w-4 h-4 shrink-0 mt-0.5" />
              <p>
                Changes to this policy take effect immediately for all mobile app users. Students attempting to order
                outside of allowed categories or during break windows will receive a clear error message.
              </p>
            </div>

            <button onClick={handleSave} disabled={saving} className="btn-primary">
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save University Policy'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
