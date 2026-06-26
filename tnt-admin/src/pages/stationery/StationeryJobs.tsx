import React, { useState, useEffect, useCallback } from 'react';
import { Printer, Search, RefreshCw, ChevronDown } from 'lucide-react';
import { type ColumnDef } from '@tanstack/react-table';
import toast from 'react-hot-toast';
import { DataTable } from '../../components/ui/DataTable';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { stationeryApi } from '../../api/stationery';
import { formatDateTime, formatTimeAgo } from '../../utils/format';
import type { PrintJob, PrintJobStatus } from '../../types';
import { cn } from '../../utils/cn';

const STATUS_FLOW: PrintJobStatus[] = ['pending', 'processing', 'ready', 'completed'];

export default function StationeryJobs() {
  const [jobs, setJobs] = useState<PrintJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<PrintJobStatus | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await stationeryApi.getJobs();
      setJobs(Array.isArray(res.data) ? res.data : []);
    } catch { toast.error('Failed to load stationery jobs'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleUpdateStatus = async (jobId: number, newStatus: string) => {
    setUpdatingId(jobId);
    try {
      await stationeryApi.updateJobStatus(jobId, newStatus);
      setJobs(prev => prev.map(j => j.id === jobId ? { ...j, status: newStatus as PrintJobStatus } : j));
      toast.success(`Job status updated to ${newStatus}`);
    } catch { toast.error('Failed to update job status'); }
    finally { setUpdatingId(null); }
  };

  const filtered = jobs.filter(j => {
    const matchSearch = !searchQuery ||
      j.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (j.user_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      String(j.id).includes(searchQuery);
    const matchStatus = statusFilter === 'all' || j.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const counts = jobs.reduce((acc, j) => {
    acc[j.status] = (acc[j.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const columns: ColumnDef<PrintJob, unknown>[] = [
    {
      accessorKey: 'id',
      header: 'Job ID',
      cell: ({ row }) => (
        <span className="font-mono text-xs text-[#9B9BC4]">#{row.original.id}</span>
      ),
    },
    {
      accessorKey: 'user_name',
      header: 'Student',
      cell: ({ row }) => (
        <div>
          <p className="font-medium text-[#F1F0FF] text-sm">{row.original.user_name || `User #${row.original.user_id}`}</p>
          <p className="text-xs text-[#9B9BC4]">{row.original.vendor_name || `Vendor #${row.original.vendor_id}`}</p>
        </div>
      ),
    },
    {
      accessorKey: 'file_name',
      header: 'File',
      cell: ({ row }) => (
        <div className="max-w-[160px]">
          <p className="text-sm text-[#F1F0FF] truncate">{row.original.file_name}</p>
          <p className="text-xs text-[#9B9BC4]">{row.original.service_name}</p>
        </div>
      ),
    },
    {
      id: 'details',
      header: 'Details',
      cell: ({ row }) => (
        <div className="text-xs text-[#9B9BC4]">
          <span className="font-mono">{row.original.pages}p</span>
          {' × '}
          <span className="font-mono">{row.original.copies}</span>
          {row.original.binding && (
            <span className="ml-1 badge bg-blue-500/20 text-blue-400 border-blue-500/30 text-[10px]">Binding</span>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge type="print_job" status={row.original.status} />,
    },
    {
      id: 'payment',
      header: 'Payment',
      cell: ({ row }) => (
        <div>
          <p className="font-mono text-sm text-[#F1F0FF]">₹{(row.original.total_amount / 100).toFixed(0)}</p>
          <p className="text-xs text-[#9B9BC4] capitalize">{row.original.payment_status}</p>
        </div>
      ),
    },
    {
      accessorKey: 'submitted_at',
      header: 'Submitted',
      cell: ({ row }) => (
        <span className="text-xs text-[#9B9BC4] font-mono">{formatTimeAgo(row.original.submitted_at)}</span>
      ),
    },
    {
      id: 'actions',
      header: 'Update Status',
      cell: ({ row }) => {
        const job = row.original;
        if (job.status === 'completed' || job.status === 'cancelled') {
          return <span className="text-xs text-[#9B9BC4]">—</span>;
        }
        const nextIdx = STATUS_FLOW.indexOf(job.status) + 1;
        const nextStatus = STATUS_FLOW[nextIdx];
        return (
          <div className="flex items-center gap-1.5">
            {nextStatus && (
              <button
                onClick={(e) => { e.stopPropagation(); handleUpdateStatus(job.id, nextStatus); }}
                disabled={updatingId === job.id}
                className="btn-primary btn-sm capitalize"
              >
                → {nextStatus}
              </button>
            )}
            <button
              onClick={(e) => { e.stopPropagation(); handleUpdateStatus(job.id, 'cancelled'); }}
              disabled={updatingId === job.id}
              className="btn-danger btn-sm"
            >
              Cancel
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-5">
      {/* Status summary */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {[
          { label: 'Pending', key: 'pending', color: 'text-amber-400' },
          { label: 'Processing', key: 'processing', color: 'text-blue-400' },
          { label: 'Ready', key: 'ready', color: 'text-green-400' },
          { label: 'Completed', key: 'completed', color: 'text-teal-400' },
          { label: 'Cancelled', key: 'cancelled', color: 'text-red-400' },
        ].map(stat => (
          <button
            key={stat.key}
            onClick={() => setStatusFilter(statusFilter === stat.key ? 'all' : stat.key as PrintJobStatus)}
            className={cn('tnt-card-sm text-center transition-all', statusFilter === stat.key && 'border-[#E85D24]/40')}
          >
            <p className={cn('text-xl font-bold font-mono', stat.color)}>{counts[stat.key] || 0}</p>
            <p className="text-[10px] text-[#9B9BC4] mt-0.5">{stat.label}</p>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9B9BC4]" />
          <input
            type="text"
            placeholder="Search by file, student, ID..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="tnt-input pl-9"
          />
        </div>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value as PrintJobStatus | 'all')}
          className="tnt-select w-40"
        >
          <option value="all">All Status</option>
          {STATUS_FLOW.map(s => (
            <option key={s} value={s} className="capitalize">{s}</option>
          ))}
          <option value="cancelled">Cancelled</option>
        </select>
        <button onClick={fetch} className="btn-ghost">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <DataTable
        data={filtered}
        columns={columns}
        loading={loading}
        emptyMessage="No print jobs found"
      />
    </div>
  );
}
