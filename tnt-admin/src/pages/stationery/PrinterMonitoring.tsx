import React, { useCallback, useEffect, useState } from 'react';
import {
  Printer as PrinterIcon, RefreshCw, Plus, Trash2, Droplet, FileStack, Layers,
  Activity, X, Loader2, IndianRupee,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import { formatRupees } from '../../utils/format';

interface Printer {
  id: number;
  vendor_id: number | null;
  vendor_name: string | null;
  name: string;
  location: string | null;
  model: string | null;
  status: string;
  queue_depth: number;
  ink_level_pct: number;
  paper_count: number;
  capacity_pages_per_hour: number;
  utilization_pct: number;
  health: string;
  last_seen_at: string | null;
}
interface Summary { total: number; online: number; offline: number; critical: number; total_queue: number; }
interface CostEntry {
  id: number; vendor_id: number | null; vendor_name: string;
  print_type: string; paper_size: string; duplex: boolean; price_per_page: number;
}

const healthColor: Record<string, string> = {
  good: 'text-green-600 bg-green-50 border-green-200',
  warning: 'text-amber-600 bg-amber-50 border-amber-200',
  critical: 'text-red-600 bg-red-50 border-red-200',
};
const statusColor: Record<string, string> = {
  online: 'text-green-600', offline: 'text-red-600', maintenance: 'text-amber-600', error: 'text-red-600',
};

function barColor(pct: number) {
  if (pct < 15) return '#DC2626';
  if (pct < 30) return '#D97706';
  return '#059669';
}

function AddPrinterModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [model, setModel] = useState('');
  const [capacity, setCapacity] = useState('600');
  const [saving, setSaving] = useState(false);
  const submit = async () => {
    if (!name.trim()) { toast.error('Name required'); return; }
    setSaving(true);
    try {
      await adminApi.createPrinter({ name: name.trim(), location: location.trim() || null, model: model.trim() || null, capacity_pages_per_hour: Number(capacity) || 600, ink_level_pct: 100, paper_count: 500 });
      toast.success('Printer registered'); onSaved(); onClose();
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Failed'); }
    finally { setSaving(false); }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="tnt-card w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[#111827]">Register Printer</h2>
          <button onClick={onClose} aria-label="Close" className="btn-ghost btn-sm"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-3">
          <input className="tnt-input" placeholder="Printer name" value={name} onChange={(e) => setName(e.target.value)} />
          <input className="tnt-input" placeholder="Location" value={location} onChange={(e) => setLocation(e.target.value)} />
          <input className="tnt-input" placeholder="Model" value={model} onChange={(e) => setModel(e.target.value)} />
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Capacity (pages/hour)</label>
            <input type="number" className="tnt-input" value={capacity} onChange={(e) => setCapacity(e.target.value)} />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="btn-ghost">Cancel</button>
          <button onClick={submit} disabled={saving} className="btn-primary">
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}Register
          </button>
        </div>
      </div>
    </div>
  );
}

export default function PrinterMonitoring() {
  const [tab, setTab] = useState<'monitor' | 'costs'>('monitor');
  const [printers, setPrinters] = useState<Printer[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [costs, setCosts] = useState<CostEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);

  // cost form
  const [ct, setCt] = useState<'bw' | 'color'>('bw');
  const [cs, setCs] = useState<'A4' | 'A3'>('A4');
  const [cd, setCd] = useState(false);
  const [cprice, setCprice] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, c] = await Promise.allSettled([adminApi.getPrinters(), adminApi.getPrintCostMatrix()]);
      if (p.status === 'fulfilled') { setPrinters(p.value.data.printers || []); setSummary(p.value.data.summary || null); }
      if (c.status === 'fulfilled') setCosts(Array.isArray(c.value.data) ? c.value.data : []);
    } catch { toast.error('Failed to load'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const removePrinter = async (id: number) => {
    if (!window.confirm('Remove this printer?')) return;
    try { await adminApi.deletePrinter(id); toast.success('Removed'); await load(); }
    catch { toast.error('Failed'); }
  };

  const saveCost = async () => {
    const rupees = parseFloat(cprice);
    if (!rupees || rupees < 0) { toast.error('Enter a price'); return; }
    try {
      await adminApi.upsertPrintCost({ print_type: ct, paper_size: cs, duplex: cd, price_per_page: rupees });
      toast.success('Price saved'); setCprice(''); await load();
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Failed'); }
  };
  const removeCost = async (id: number) => {
    try { await adminApi.deletePrintCost(id); toast.success('Deleted'); await load(); }
    catch { toast.error('Failed'); }
  };

  return (
    <div className="space-y-5">
      {showAdd && <AddPrinterModal onClose={() => setShowAdd(false)} onSaved={load} />}

      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-1 p-1 bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl w-fit">
          <button onClick={() => setTab('monitor')} className={`tab-btn ${tab === 'monitor' ? 'active' : ''} flex items-center gap-2`}>
            <Activity className="w-4 h-4" /> Printer Monitoring
          </button>
          <button onClick={() => setTab('costs')} className={`tab-btn ${tab === 'costs' ? 'active' : ''} flex items-center gap-2`}>
            <IndianRupee className="w-4 h-4" /> Print Cost Matrix
          </button>
        </div>
        <div className="flex gap-2">
          {tab === 'monitor' && (
            <button onClick={() => setShowAdd(true)} className="btn-primary"><Plus className="w-4 h-4" /> Add Printer</button>
          )}
          <button onClick={load} className="btn-ghost" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
        </div>
      </div>

      {tab === 'monitor' && summary && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { label: 'Printers', value: summary.total, color: 'text-[#111827]' },
            { label: 'Online', value: summary.online, color: 'text-green-600' },
            { label: 'Offline', value: summary.offline, color: 'text-red-600' },
            { label: 'Critical', value: summary.critical, color: 'text-red-600' },
            { label: 'Queue', value: summary.total_queue, color: 'text-[#E85D24]' },
          ].map((s) => (
            <div key={s.label} className="tnt-card">
              <p className="text-xs text-[#6B7280]">{s.label}</p>
              <p className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="skeleton h-80 rounded-xl" />
      ) : tab === 'monitor' ? (
        printers.length === 0 ? (
          <div className="tnt-card text-center py-16">
            <PrinterIcon className="w-12 h-12 text-[#D1D5DB] mx-auto mb-3" />
            <p className="text-[#4B5563]">No printers registered yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {printers.map((p) => (
              <div key={p.id} className="tnt-card">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center">
                      <PrinterIcon className="w-5 h-5 text-[#E85D24]" />
                    </div>
                    <div>
                      <p className="font-semibold text-[#111827]">{p.name}</p>
                      <p className="text-xs text-[#9CA3AF]">{p.location || p.vendor_name || '—'}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs border ${healthColor[p.health]}`}>{p.health}</span>
                </div>
                <div className="flex items-center justify-between text-xs mb-3">
                  <span className={`font-medium capitalize ${statusColor[p.status] || 'text-[#6B7280]'}`}>● {p.status}</span>
                  <span className="text-[#6B7280]">{p.model || ''}</span>
                </div>
                {/* Ink */}
                <div className="mb-2">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="flex items-center gap-1 text-[#6B7280]"><Droplet className="w-3 h-3" /> Ink</span>
                    <span className="font-mono">{p.ink_level_pct}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-[#F3F4F6] overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${p.ink_level_pct}%`, backgroundColor: barColor(p.ink_level_pct) }} />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs mt-3">
                  <div className="flex flex-col items-center p-2 rounded-lg bg-[#F9FAFB]">
                    <FileStack className="w-4 h-4 text-[#6B7280] mb-1" />
                    <span className="font-mono font-semibold">{p.paper_count}</span>
                    <span className="text-[#9CA3AF]">paper</span>
                  </div>
                  <div className="flex flex-col items-center p-2 rounded-lg bg-[#F9FAFB]">
                    <Layers className="w-4 h-4 text-[#6B7280] mb-1" />
                    <span className="font-mono font-semibold">{p.queue_depth}</span>
                    <span className="text-[#9CA3AF]">queue</span>
                  </div>
                  <div className="flex flex-col items-center p-2 rounded-lg bg-[#F9FAFB]">
                    <Activity className="w-4 h-4 text-[#6B7280] mb-1" />
                    <span className="font-mono font-semibold">{p.utilization_pct}%</span>
                    <span className="text-[#9CA3AF]">util</span>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <span className="text-[10px] text-[#9CA3AF]">Cap {p.capacity_pages_per_hour}/hr</span>
                  <button onClick={() => removePrinter(p.id)} aria-label="Remove printer" className="btn-ghost btn-sm text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        <div className="space-y-4">
          {/* Add/override price */}
          <div className="tnt-card">
            <h3 className="text-sm font-semibold text-[#374151] mb-3">Set / Override Price</h3>
            <div className="flex flex-wrap gap-3 items-end">
              <div>
                <label className="text-xs text-[#6B7280] mb-1 block">Type</label>
                <select aria-label="Print type" className="tnt-select w-28" value={ct} onChange={(e) => setCt(e.target.value as 'bw' | 'color')}>
                  <option value="bw">B/W</option><option value="color">Color</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-[#6B7280] mb-1 block">Paper</label>
                <select aria-label="Paper size" className="tnt-select w-24" value={cs} onChange={(e) => setCs(e.target.value as 'A4' | 'A3')}>
                  <option value="A4">A4</option><option value="A3">A3</option>
                </select>
              </div>
              <label className="flex items-center gap-1 text-sm text-[#374151] pb-2">
                <input type="checkbox" checked={cd} onChange={(e) => setCd(e.target.checked)} /> Duplex
              </label>
              <div>
                <label className="text-xs text-[#6B7280] mb-1 block">₹ / page</label>
                <input type="number" step="0.01" className="tnt-input w-28" value={cprice} onChange={(e) => setCprice(e.target.value)} placeholder="2.00" />
              </div>
              <button onClick={saveCost} className="btn-primary">Save Price</button>
            </div>
          </div>
          {/* Matrix table */}
          <div className="tnt-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-[#6B7280] border-b border-[#E5E7EB]">
                  <th className="py-2 px-3">Scope</th><th className="py-2 px-3">Type</th><th className="py-2 px-3">Paper</th>
                  <th className="py-2 px-3">Duplex</th><th className="py-2 px-3">Price / page</th><th className="py-2 px-3"></th>
                </tr>
              </thead>
              <tbody>
                {costs.length === 0 && <tr><td colSpan={6} className="py-8 text-center text-[#9CA3AF]">No pricing set</td></tr>}
                {costs.map((c) => (
                  <tr key={c.id} className="border-b border-[#F3F4F6]">
                    <td className="py-2 px-3">{c.vendor_name}</td>
                    <td className="py-2 px-3 uppercase">{c.print_type}</td>
                    <td className="py-2 px-3">{c.paper_size}</td>
                    <td className="py-2 px-3">{c.duplex ? 'Yes' : 'No'}</td>
                    <td className="py-2 px-3 font-mono font-semibold">{formatRupees(c.price_per_page)}</td>
                    <td className="py-2 px-3">
                      <button onClick={() => removeCost(c.id)} aria-label="Delete price" className="btn-ghost btn-sm text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
