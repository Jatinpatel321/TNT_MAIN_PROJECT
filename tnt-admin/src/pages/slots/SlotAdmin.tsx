import React, { useCallback, useEffect, useState } from 'react';
import { Clock, LayoutTemplate, Plus, Trash2, Zap, Loader2, RefreshCw, Save, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';

interface SlotTemplate {
  id: number;
  name: string;
  vendor_id: number | null;
  vendor_name: string;
  day_of_week: number | null;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
  max_orders_per_slot: number;
  is_active: boolean;
}
interface Vendor { id: number; name: string; }

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function SlotAdmin() {
  const [config, setConfig] = useState<Record<string, string>>({});
  const [templates, setTemplates] = useState<SlotTemplate[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingCfg, setSavingCfg] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [genFor, setGenFor] = useState<SlotTemplate | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [c, t, v] = await Promise.allSettled([adminApi.getSlotConfig(), adminApi.getSlotTemplates(), adminApi.getVendors()]);
      if (c.status === 'fulfilled') setConfig(c.value.data || {});
      if (t.status === 'fulfilled') setTemplates(Array.isArray(t.value.data) ? t.value.data : []);
      if (v.status === 'fulfilled') setVendors((Array.isArray(v.value.data) ? v.value.data : []).map((x: any) => ({ id: x.id, name: x.name })));
    } catch { toast.error('Failed to load slot management'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const saveConfig = async () => {
    setSavingCfg(true);
    try { await adminApi.setSlotConfig(config); toast.success('Global config saved'); }
    catch { toast.error('Failed'); }
    finally { setSavingCfg(false); }
  };
  const cfgField = (key: string, val: string) => setConfig(prev => ({ ...prev, [key]: val }));

  const removeTemplate = async (id: number) => {
    if (!window.confirm('Delete this template?')) return;
    try { await adminApi.deleteSlotTemplate(id); toast.success('Deleted'); await load(); }
    catch { toast.error('Failed'); }
  };

  return (
    <div className="space-y-6">
      {showCreate && <TemplateModal vendors={vendors} onClose={() => setShowCreate(false)} onSaved={load} />}
      {genFor && <GenerateModal template={genFor} vendors={vendors} onClose={() => setGenFor(null)} onDone={load} />}

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#111827]">Slot Management</h2>
          <p className="text-sm text-[#6B7280] mt-1">Campus slot defaults & reusable generation templates</p>
        </div>
        <button onClick={load} className="btn-ghost" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
      </div>

      {/* Global config */}
      <div className="tnt-card">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-5 h-5 text-[#4F46E5]" />
          <h3 className="font-semibold text-[#111827]">Global Slot Configuration</h3>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Default duration (min)</label>
            <input type="number" className="tnt-input" value={config.slot_default_duration_minutes || ''} onChange={(e) => cfgField('slot_default_duration_minutes', e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Default capacity</label>
            <input type="number" className="tnt-input" value={config.slot_default_capacity || ''} onChange={(e) => cfgField('slot_default_capacity', e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Campus opens</label>
            <input type="time" className="tnt-input" value={config.campus_open_time || ''} onChange={(e) => cfgField('campus_open_time', e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Campus closes</label>
            <input type="time" className="tnt-input" value={config.campus_close_time || ''} onChange={(e) => cfgField('campus_close_time', e.target.value)} />
          </div>
        </div>
        <div className="flex justify-end mt-4">
          <button onClick={saveConfig} disabled={savingCfg} className="btn-primary">
            {savingCfg ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Save Config
          </button>
        </div>
      </div>

      {/* Templates */}
      <div className="tnt-card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <LayoutTemplate className="w-5 h-5 text-[#E85D24]" />
            <h3 className="font-semibold text-[#111827]">Slot Templates</h3>
          </div>
          <button onClick={() => setShowCreate(true)} className="btn-primary btn-sm"><Plus className="w-3.5 h-3.5" /> New Template</button>
        </div>
        {loading ? (
          <div className="skeleton h-40 rounded-xl" />
        ) : templates.length === 0 ? (
          <p className="text-center py-10 text-[#9CA3AF]">No templates yet. Create one to generate slots in bulk.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-[#6B7280] border-b border-[#E5E7EB]">
                  <th className="py-2 px-3">Name</th><th className="py-2 px-3">Vendor</th><th className="py-2 px-3">Days</th>
                  <th className="py-2 px-3">Window</th><th className="py-2 px-3">Slot</th><th className="py-2 px-3">Cap</th><th className="py-2 px-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((t) => (
                  <tr key={t.id} className="border-b border-[#F3F4F6]">
                    <td className="py-2 px-3 font-medium text-[#111827]">{t.name}</td>
                    <td className="py-2 px-3 text-[#6B7280]">{t.vendor_name}</td>
                    <td className="py-2 px-3">{t.day_of_week === null ? 'All days' : DAYS[t.day_of_week]}</td>
                    <td className="py-2 px-3 font-mono">{t.start_time}–{t.end_time}</td>
                    <td className="py-2 px-3 font-mono">{t.slot_duration_minutes}m</td>
                    <td className="py-2 px-3 font-mono">{t.max_orders_per_slot}</td>
                    <td className="py-2 px-3">
                      <div className="flex gap-1">
                        <button onClick={() => setGenFor(t)} className="btn-success btn-sm"><Zap className="w-3.5 h-3.5" /> Generate</button>
                        <button onClick={() => removeTemplate(t.id)} aria-label="Delete template" className="btn-ghost btn-sm text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function TemplateModal({ vendors, onClose, onSaved }: { vendors: Vendor[]; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState('');
  const [vendorId, setVendorId] = useState<string>('');
  const [dow, setDow] = useState<string>('');
  const [start, setStart] = useState('10:00');
  const [end, setEnd] = useState('12:00');
  const [duration, setDuration] = useState('30');
  const [cap, setCap] = useState('10');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!name.trim()) { toast.error('Name required'); return; }
    setSaving(true);
    try {
      await adminApi.createSlotTemplate({
        name: name.trim(),
        vendor_id: vendorId ? Number(vendorId) : null,
        day_of_week: dow === '' ? null : Number(dow),
        start_time: start, end_time: end,
        slot_duration_minutes: Number(duration) || 30,
        max_orders_per_slot: Number(cap) || 10,
      });
      toast.success('Template created'); onSaved(); onClose();
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Failed'); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="tnt-card w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[#111827]">New Slot Template</h2>
          <button onClick={onClose} aria-label="Close" className="btn-ghost btn-sm"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-3">
          <input className="tnt-input" placeholder="Template name" value={name} onChange={(e) => setName(e.target.value)} />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">Vendor</label>
              <select aria-label="Vendor" className="tnt-select" value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
                <option value="">Any vendor</option>
                {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">Day</label>
              <select aria-label="Day of week" className="tnt-select" value={dow} onChange={(e) => setDow(e.target.value)}>
                <option value="">All days</option>
                {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div><label className="text-xs text-[#6B7280] mb-1 block">Opens</label><input type="time" className="tnt-input" value={start} onChange={(e) => setStart(e.target.value)} /></div>
            <div><label className="text-xs text-[#6B7280] mb-1 block">Closes</label><input type="time" className="tnt-input" value={end} onChange={(e) => setEnd(e.target.value)} /></div>
            <div><label className="text-xs text-[#6B7280] mb-1 block">Slot min</label><input type="number" className="tnt-input" value={duration} onChange={(e) => setDuration(e.target.value)} /></div>
            <div><label className="text-xs text-[#6B7280] mb-1 block">Capacity</label><input type="number" className="tnt-input" value={cap} onChange={(e) => setCap(e.target.value)} /></div>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="btn-ghost">Cancel</button>
          <button onClick={submit} disabled={saving} className="btn-primary">{saving && <Loader2 className="w-4 h-4 animate-spin" />} Create</button>
        </div>
      </div>
    </div>
  );
}

function GenerateModal({ template, vendors, onClose, onDone }: { template: SlotTemplate; vendors: Vendor[]; onClose: () => void; onDone: () => void }) {
  const [vendorId, setVendorId] = useState<string>(template.vendor_id ? String(template.vendor_id) : '');
  const today = new Date().toISOString().slice(0, 10);
  const [from, setFrom] = useState(today);
  const [to, setTo] = useState(today);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (!vendorId) { toast.error('Pick a vendor'); return; }
    setBusy(true);
    try {
      const res = await adminApi.generateSlotsFromTemplate(template.id, { vendor_id: Number(vendorId), date_from: from, date_to: to });
      toast.success(`Created ${res.data.created} slots (${res.data.skipped} already existed)`);
      onDone(); onClose();
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Failed'); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="tnt-card w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[#111827]">Generate Slots — {template.name}</h2>
          <button onClick={onClose} aria-label="Close" className="btn-ghost btn-sm"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Vendor</label>
            <select aria-label="Vendor" className="tnt-select w-full" value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
              <option value="">Select vendor</option>
              {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs text-[#6B7280] mb-1 block">From</label><input type="date" className="tnt-input" value={from} onChange={(e) => setFrom(e.target.value)} /></div>
            <div><label className="text-xs text-[#6B7280] mb-1 block">To</label><input type="date" className="tnt-input" value={to} onChange={(e) => setTo(e.target.value)} /></div>
          </div>
          <p className="text-xs text-[#9CA3AF]">Generates {template.start_time}–{template.end_time} slots ({template.slot_duration_minutes}m, cap {template.max_orders_per_slot}). Existing slots are skipped.</p>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="btn-ghost">Cancel</button>
          <button onClick={run} disabled={busy} className="btn-success">{busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />} Generate</button>
        </div>
      </div>
    </div>
  );
}
