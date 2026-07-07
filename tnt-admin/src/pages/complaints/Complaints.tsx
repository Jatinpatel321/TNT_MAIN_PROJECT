import React, { useState, useEffect, useCallback } from 'react';
import {
  MessageSquareWarning, Search, X, ChevronDown,
  User, Store, CheckCircle, ArrowUp, Filter,
} from 'lucide-react';
import { type ColumnDef } from '@tanstack/react-table';
import toast from 'react-hot-toast';
import { DataTable } from '../../components/ui/DataTable';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { complaintsApi } from '../../api/complaints';
import { formatDate, formatTimeAgo, truncate } from '../../utils/format';
import type { Complaint, ComplaintStatus } from '../../types';
import { cn } from '../../utils/cn';

export default function Complaints() {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Complaint | null>(null);
  const [statusFilter, setStatusFilter] = useState<ComplaintStatus | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await complaintsApi.getAll();
      const data = Array.isArray(res.data) ? res.data : [];
      setComplaints(data);
    } catch {
      toast.error('Failed to load complaints');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleUpdateStatus = async (id: number, status: string) => {
    setActionLoading(true);
    try {
      await complaintsApi.updateStatus(id, status);
      setComplaints(prev => prev.map(c => c.id === id ? { ...c, status: status as ComplaintStatus } : c));
      if (selected?.id === id) setSelected(prev => prev ? { ...prev, status: status as ComplaintStatus } : null);
      toast.success(`Complaint marked as ${status}`);
    } catch { toast.error('Failed to update status'); }
    finally { setActionLoading(false); }
  };

  const handleEscalate = async (id: number) => {
    setActionLoading(true);
    try {
      await complaintsApi.escalate(id);
      setComplaints(prev => prev.map(c => c.id === id ? { ...c, status: 'escalated' } : c));
      if (selected?.id === id) setSelected(prev => prev ? { ...prev, status: 'escalated' } : null);
      toast.success('Complaint escalated');
    } catch { toast.error('Failed to escalate'); }
    finally { setActionLoading(false); }
  };

  const filtered = complaints.filter(c => {
    const matchSearch = !searchQuery ||
      c.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.user_name || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchStatus = statusFilter === 'all' || c.status === statusFilter;
    return matchSearch && matchStatus;
  });

  // Status counts
  const counts = complaints.reduce((acc, c) => {
    acc[c.status] = (acc[c.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const columns: ColumnDef<Complaint, unknown>[] = [
    {
      accessorKey: 'id',
      header: 'ID',
      cell: ({ row }) => (
        <span className="font-mono text-xs text-[#6B7280]">#{row.original.id}</span>
      ),
    },
    {
      accessorKey: 'user_name',
      header: 'Student',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 text-xs font-bold shrink-0">
            {(row.original.user_name || 'U').charAt(0)}
          </div>
          <span className="text-sm text-[#111827]">{row.original.user_name || `User #${row.original.user_id}`}</span>
        </div>
      ),
    },
    {
      accessorKey: 'category',
      header: 'Category',
      cell: ({ row }) => (
        <span className="badge bg-[#F3F5F9] text-[#6B7280] border-[#E5E7EB]">{row.original.category}</span>
      ),
    },
    {
      accessorKey: 'description',
      header: 'Description',
      cell: ({ row }) => (
        <span className="text-xs text-[#4B5563]">{truncate(row.original.description, 60)}</span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge type="complaint" status={row.original.status} />,
    },
    {
      accessorKey: 'created_at',
      header: 'Filed',
      cell: ({ row }) => (
        <span className="text-xs text-[#6B7280] font-mono whitespace-nowrap">
          {formatTimeAgo(row.original.created_at)}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const c = row.original;
        return (
          <div className="flex items-center gap-1.5">
            {c.status !== 'resolved' && (
              <button
                onClick={(e) => { e.stopPropagation(); handleUpdateStatus(c.id, 'resolved'); }}
                disabled={actionLoading}
                className="btn-success btn-sm"
              >
                <CheckCircle className="w-3 h-3" />
              </button>
            )}
            {c.status !== 'escalated' && (
              <button
                onClick={(e) => { e.stopPropagation(); handleEscalate(c.id); }}
                disabled={actionLoading}
                className="btn-ghost btn-sm text-purple-400 border-purple-500/30"
              >
                <ArrowUp className="w-3 h-3" />
              </button>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-5">
      {/* Status summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Open', key: 'open', color: 'text-red-500', bg: 'bg-red-500/10' },
          { label: 'Assigned', key: 'assigned', color: 'text-amber-500', bg: 'bg-amber-500/10' },
          { label: 'Escalated', key: 'escalated', color: 'text-purple-500', bg: 'bg-purple-500/10' },
          { label: 'Resolved', key: 'resolved', color: 'text-green-500', bg: 'bg-green-500/10' },
        ].map(stat => (
          <button
            key={stat.key}
            onClick={() => setStatusFilter(statusFilter === stat.key ? 'all' : stat.key as ComplaintStatus)}
            className={cn(
              'tnt-card-sm text-center transition-all duration-200',
              statusFilter === stat.key && 'border-[#E85D24]/40'
            )}
          >
            <p className={cn('text-2xl font-bold font-mono', stat.color)}>{counts[stat.key] || 0}</p>
            <p className="text-xs text-[#6B7280] mt-0.5">{stat.label}</p>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6B7280]" />
          <input
            type="text"
            placeholder="Search complaints..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="tnt-input pl-9"
          />
        </div>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value as ComplaintStatus | 'all')}
          className="tnt-select w-40"
        >
          <option value="all">All Status</option>
          <option value="open">Open</option>
          <option value="assigned">Assigned</option>
          <option value="resolved">Resolved</option>
          <option value="escalated">Escalated</option>
        </select>
      </div>

      {/* Table */}
      <DataTable
        data={filtered}
        columns={columns}
        loading={loading}
        onRowClick={c => setSelected(c)}
        emptyMessage="No complaints found"
      />

      {/* Detail Slide-over */}
      {selected && (
        <>
          <div className="fixed inset-0 bg-black/40 z-40" onClick={() => setSelected(null)} />
          <div className="slide-over">
            <div className="flex items-center justify-between p-5 border-b border-[#E5E7EB]">
              <h2 className="text-lg font-semibold text-[#111827]">Complaint #{selected.id}</h2>
              <button onClick={() => setSelected(null)} className="btn-ghost btn-sm">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 space-y-5">
              {/* Status + Category */}
              <div className="flex items-center gap-2 flex-wrap">
                <StatusBadge type="complaint" status={selected.status} />
                <span className="badge bg-[#F3F5F9] text-[#6B7280] border-[#E5E7EB]">{selected.category}</span>
              </div>

              {/* Details */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <User className="w-4 h-4 text-[#6B7280]" />
                  <span className="text-[#6B7280]">Filed by:</span>
                  <span className="text-[#111827] font-medium">
                    {selected.user_name || `User #${selected.user_id}`}
                  </span>
                </div>
                {selected.vendor_id && (
                <div className="flex items-center gap-2 text-sm">
                  <Store className="w-4 h-4 text-[#6B7280]" />
                  <span className="text-[#6B7280]">Against:</span>
                  <span className="text-[#111827] font-medium">
                    {selected.vendor_name || `Vendor #${selected.vendor_id}`}
                  </span>
                </div>
                )}
                <div className="text-sm text-[#6B7280]">Filed {formatTimeAgo(selected.created_at)}</div>
              </div>

              {/* Description */}
              <div>
                <label className="tnt-label">Full Description</label>
                <div className="bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg p-4 text-sm text-[#111827] leading-relaxed">
                  {selected.description}
                </div>
              </div>

              {/* Actions */}
              <div className="space-y-2">
                <label className="tnt-label">Update Status</label>
                <div className="grid grid-cols-2 gap-2">
                  {(['open', 'assigned', 'resolved', 'escalated'] as ComplaintStatus[]).map(s => (
                    <button
                      key={s}
                      onClick={() => handleUpdateStatus(selected.id, s)}
                      disabled={actionLoading || selected.status === s}
                      className={cn(
                        'btn-ghost justify-center capitalize text-xs py-2',
                        selected.status === s && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              {selected.status !== 'escalated' && (
                <button
                  onClick={() => handleEscalate(selected.id)}
                  disabled={actionLoading}
                  className="btn-ghost w-full justify-center text-purple-400 border-purple-500/30"
                >
                  <ArrowUp className="w-4 h-4" /> Escalate to Senior Admin
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
