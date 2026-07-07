import React, { useState, useEffect, useCallback } from 'react';
import { BookOpen, Download, IndianRupee, TrendingUp, TrendingDown, Search, Calendar, Plus, X, Loader2 } from 'lucide-react';
import { type ColumnDef } from '@tanstack/react-table';
import toast from 'react-hot-toast';
import { DataTable } from '../../components/ui/DataTable';
import { adminApi } from '../../api/admin';
import { formatDateTime, formatPaise, formatCurrency } from '../../utils/format';
import type { LedgerEntry } from '../../types';
import { cn } from '../../utils/cn';

function exportToCsv(data: LedgerEntry[], filename: string) {
  const headers = ['ID', 'User', 'Type', 'Amount (₹)', 'Description', 'Order ID', 'Timestamp'];
  const rows = data.map(e => [
    e.id,
    e.user_name || `User #${e.user_id}`,
    e.type,
    (e.amount / 100).toFixed(2),
    `"${e.description.replace(/"/g, '""')}"`,
    e.order_id || '',
    e.timestamp,
  ]);
  const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function AdjustmentModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [type, setType] = useState<'credit' | 'debit'>('credit');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [orderId, setOrderId] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    const rupees = parseFloat(amount);
    if (!rupees || rupees <= 0) { toast.error('Enter a valid amount'); return; }
    if (!description.trim()) { toast.error('Description is required'); return; }
    setSaving(true);
    try {
      await adminApi.addLedgerAdjustment({
        type,
        amount: Math.round(rupees * 100),
        description: description.trim(),
        order_id: orderId ? Number(orderId) : null,
      });
      toast.success('Adjustment recorded');
      onSaved();
      onClose();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to record adjustment');
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="tnt-card w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[#111827]">Manual Ledger Adjustment</h2>
          <button onClick={onClose} aria-label="Close" className="btn-ghost btn-sm"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Type</label>
            <select aria-label="Adjustment type" className="tnt-select" value={type} onChange={(e) => setType(e.target.value as 'credit' | 'debit')}>
              <option value="credit">Credit (inflow)</option>
              <option value="debit">Debit (outflow)</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Amount (₹)</label>
            <input type="number" className="tnt-input" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" />
          </div>
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Description</label>
            <input className="tnt-input" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Reason for adjustment" />
          </div>
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Order ID (optional)</label>
            <input type="number" className="tnt-input" value={orderId} onChange={(e) => setOrderId(e.target.value)} placeholder="Link to an order" />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="btn-ghost">Cancel</button>
          <button onClick={submit} disabled={saving} className="btn-primary">
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            Record Adjustment
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Ledger() {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState<'all' | 'credit' | 'debit'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showAdjust, setShowAdjust] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getLedger();
      setEntries(Array.isArray(res.data) ? res.data : []);
    } catch { toast.error('Failed to load ledger'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const filtered = entries.filter(e => {
    const matchType = typeFilter === 'all' || e.type === typeFilter;
    const matchSearch = !searchQuery ||
      (e.user_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      String(e.order_id || '').includes(searchQuery);
    const matchDate = (!dateFrom || new Date(e.timestamp) >= new Date(dateFrom)) &&
                      (!dateTo   || new Date(e.timestamp) <= new Date(dateTo + 'T23:59:59'));
    return matchType && matchSearch && matchDate;
  });

  const totalInflow = filtered
    .filter(e => e.type === 'credit')
    .reduce((a, e) => a + e.amount, 0);

  const totalOutflow = filtered
    .filter(e => e.type === 'debit')
    .reduce((a, e) => a + e.amount, 0);

  const netBalance = totalInflow - totalOutflow;

  const handleExport = () => {
    exportToCsv(filtered, `tnt-ledger-${new Date().toISOString().split('T')[0]}.csv`);
    toast.success('Ledger exported to CSV');
  };

  const columns: ColumnDef<LedgerEntry, unknown>[] = [
    {
      accessorKey: 'id',
      header: 'Entry ID',
      cell: ({ row }) => (
        <span className="font-mono text-xs text-[#6B7280]">#{row.original.id}</span>
      ),
    },
    {
      accessorKey: 'user_name',
      header: 'User',
      cell: ({ row }) => (
        <span className="text-sm text-[#111827]">
          {row.original.user_name || `User #${row.original.user_id}`}
        </span>
      ),
    },
    {
      accessorKey: 'type',
      header: 'Type',
      cell: ({ row }) => (
        <div className="flex items-center gap-1.5">
          {row.original.type === 'credit' ? (
            <TrendingUp className="w-3.5 h-3.5 text-green-500" />
          ) : (
            <TrendingDown className="w-3.5 h-3.5 text-red-500" />
          )}
          <span className={cn(
            'text-xs font-medium capitalize',
            row.original.type === 'credit' ? 'text-green-500' : 'text-red-500'
          )}>
            {row.original.type}
          </span>
        </div>
      ),
    },
    {
      accessorKey: 'amount',
      header: 'Amount',
      cell: ({ row }) => (
        <span className={cn(
          'font-mono font-bold text-sm',
          row.original.type === 'credit' ? 'text-green-500' : 'text-red-500'
        )}>
          {row.original.type === 'credit' ? '+' : '-'}{formatCurrency(row.original.amount, { showDecimals: true })}
        </span>
      ),
    },
    {
      accessorKey: 'description',
      header: 'Description',
      cell: ({ row }) => (
        <span className="text-xs text-[#4B5563] max-w-[200px] truncate block">
          {row.original.description}
        </span>
      ),
    },
    {
      accessorKey: 'order_id',
      header: 'Order',
      cell: ({ row }) => (
        <span className="font-mono text-xs text-[#6B7280]">
          {row.original.order_id ? `#${row.original.order_id}` : '—'}
        </span>
      ),
    },
    {
      accessorKey: 'timestamp',
      header: 'Date & Time',
      cell: ({ row }) => (
        <span className="text-xs font-mono text-[#6B7280] whitespace-nowrap">
          {formatDateTime(row.original.timestamp)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {showAdjust && <AdjustmentModal onClose={() => setShowAdjust(false)} onSaved={fetch} />}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="tnt-card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-green-500" />
            <span className="text-xs text-[#6B7280]">Total Inflow</span>
          </div>
          <p className="text-2xl font-bold font-mono text-green-500">+{formatPaise(totalInflow)}</p>
          <p className="text-xs text-[#6B7280] mt-1">{filtered.filter(e => e.type === 'credit').length} credit entries</p>
        </div>
        <div className="tnt-card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-red-500" />
            <span className="text-xs text-[#6B7280]">Total Outflow</span>
          </div>
          <p className="text-2xl font-bold font-mono text-red-500">-{formatPaise(totalOutflow)}</p>
          <p className="text-xs text-[#6B7280] mt-1">{filtered.filter(e => e.type === 'debit').length} debit entries</p>
        </div>
        <div className="tnt-card">
          <div className="flex items-center gap-2 mb-2">
            <IndianRupee className="w-4 h-4 text-[#E85D24]" />
            <span className="text-xs text-[#6B7280]">Net Balance</span>
          </div>
          <p className={cn('text-2xl font-bold font-mono', netBalance >= 0 ? 'text-[#E85D24]' : 'text-red-500')}>
            {netBalance >= 0 ? '+' : ''}{formatPaise(Math.abs(netBalance))}
          </p>
          <p className="text-xs text-[#6B7280] mt-1">{filtered.length} total entries</p>
        </div>
      </div>

      {/* Filters + Export */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6B7280]" />
          <input
            type="text"
            placeholder="Search user, description, order..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="tnt-input pl-9"
          />
        </div>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value as typeof typeFilter)} className="tnt-select w-36">
          <option value="all">All Types</option>
          <option value="credit">Credit</option>
          <option value="debit">Debit</option>
        </select>
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-[#6B7280]" />
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="tnt-input w-36 text-sm" />
          <span className="text-[#6B7280] text-sm">to</span>
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="tnt-input w-36 text-sm" />
        </div>
        <div className="ml-auto flex gap-2">
          <button onClick={() => setShowAdjust(true)} className="btn-primary">
            <Plus className="w-4 h-4" />
            Add Adjustment
          </button>
          <button onClick={handleExport} className="btn-ghost">
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      <DataTable
        data={filtered}
        columns={columns}
        loading={loading}
        emptyMessage="No ledger entries found"
      />
    </div>
  );
}
