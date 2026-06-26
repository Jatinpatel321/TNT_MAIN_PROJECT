import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Filter, Store, CheckCircle, XCircle, Eye, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { type ColumnDef } from '@tanstack/react-table';
import { DataTable } from '../../components/ui/DataTable';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { vendorsApi } from '../../api/vendors';
import { adminApi } from '../../api/admin';
import { formatDate, formatNumber } from '../../utils/format';
import type { Vendor } from '../../types';

type VendorTab = 'all' | 'pending' | 'rejected';

export default function VendorList() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as VendorTab) || 'all';

  const [tab, setTab] = useState<VendorTab>(initialTab);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [pendingVendors, setPendingVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'food' | 'stationery'>('all');
  const [approvingId, setApprovingId] = useState<number | null>(null);

  const fetchVendors = useCallback(async () => {
    setLoading(true);
    try {
      const [allRes, pendingRes] = await Promise.allSettled([
        vendorsApi.getAll(),
        adminApi.getPendingVendors(),
      ]);
      if (allRes.status === 'fulfilled') {
        setVendors(Array.isArray(allRes.value.data) ? allRes.value.data : []);
      }
      if (pendingRes.status === 'fulfilled') {
        setPendingVendors(Array.isArray(pendingRes.value.data) ? pendingRes.value.data : []);
      }
    } catch {
      toast.error('Failed to load vendors');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchVendors(); }, [fetchVendors]);

  const handleApprove = async (id: number) => {
    setApprovingId(id);
    try {
      await adminApi.approveVendor(id);
      setPendingVendors(prev => prev.filter(v => v.id !== id));
      toast.success('Vendor approved — now visible in mobile app');
    } catch { toast.error('Failed to approve'); }
    finally { setApprovingId(null); }
  };

  const handleReject = async (id: number) => {
    setApprovingId(id);
    try {
      await adminApi.rejectVendor(id);
      setPendingVendors(prev => prev.filter(v => v.id !== id));
      toast.success('Vendor rejected');
    } catch { toast.error('Failed to reject'); }
    finally { setApprovingId(null); }
  };

  const isPending = (v: Vendor) => !v.is_approved && v.is_active !== false;
  const isRejected = (v: Vendor) => !v.is_approved && v.is_active === false;
  const isApproved = (v: Vendor) => v.is_approved === true;

  const filteredVendors = vendors.filter(v => {
    const matchSearch = !searchQuery ||
      v.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      v.phone.includes(searchQuery);
    const matchType = typeFilter === 'all' || v.vendor_type === typeFilter;
    const matchTab =
      tab === 'all'      ? isApproved(v) :
      tab === 'pending'  ? isPending(v) :
      tab === 'rejected' ? isRejected(v) : true;
    return matchSearch && matchType && matchTab;
  });

  const columns: ColumnDef<Vendor, unknown>[] = [
    {
      accessorKey: 'name',
      header: 'Vendor',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center shrink-0">
            <Store className="w-4 h-5 text-[#E85D24]" />
          </div>
          <div>
            <p className="font-medium text-[#111827]">{row.original.name}</p>
            <p className="text-xs text-[#9CA3AF]">{row.original.phone}</p>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'vendor_type',
      header: 'Type',
      cell: ({ row }) => <StatusBadge type="vendor_type" status={row.original.vendor_type} />,
    },
    {
      accessorKey: 'location',
      header: 'Location',
      cell: ({ row }) => (
        <span className="text-[#9CA3AF] text-xs">{row.original.location || '—'}</span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const v = row.original;
        if (!v.is_approved) return <StatusBadge type="vendor" status="pending" />;
        if (!v.is_active) return <StatusBadge type="vendor" status="inactive" />;
        return <StatusBadge type="vendor" status="approved" />;
      },
    },
    {
      accessorKey: 'rating',
      header: 'Rating',
      cell: ({ row }) => (
        <span className="font-mono text-sm text-[#111827]">
          {row.original.rating ? `⭐ ${row.original.rating.toFixed(1)}` : '—'}
        </span>
      ),
    },
    {
      accessorKey: 'created_at',
      header: 'Joined',
      cell: ({ row }) => (
        <span className="text-xs text-[#9CA3AF] font-mono">{formatDate(row.original.created_at)}</span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); navigate(`/vendors/${row.original.id}`); }}
            className="btn-ghost btn-sm"
          >
            <Eye className="w-3.5 h-3.5" />
            View
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl w-fit">
        {(['all', 'pending', 'rejected'] as VendorTab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`tab-btn ${tab === t ? 'active' : ''} capitalize flex items-center gap-2`}
          >
            {t === 'pending' && pendingVendors.length > 0 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-50 text-amber-600 border border-amber-200">
                {pendingVendors.length}
              </span>
            )}
            {t} Vendors
          </button>
        ))}
      </div>

      {/* All Vendors Tab */}
      {tab === 'all' && (
        <>
          {/* Filters */}
          <div className="flex flex-wrap gap-3 items-center">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
              <input
                type="text"
                placeholder="Search vendors..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="tnt-input pl-9"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as typeof typeFilter)}
              className="tnt-select w-40"
            >
              <option value="all">All Types</option>
              <option value="food">Food Court</option>
              <option value="stationery">Stationery</option>
            </select>
            <button onClick={fetchVendors} className="btn-ghost">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <DataTable
            data={filteredVendors}
            columns={columns}
            loading={loading}
            onRowClick={(vendor) => navigate(`/vendors/${vendor.id}`)}
            emptyMessage="No vendors found"
          />
        </>
      )}

      {/* Pending Approval Tab */}
      {tab === 'pending' && (
        <div>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map(i => <div key={i} className="skeleton h-44 rounded-xl" />)}
            </div>
          ) : pendingVendors.length === 0 ? (
            <div className="tnt-card text-center py-16">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-[#111827] mb-1">All caught up!</h3>
              <p className="text-[#4B5563]">No vendors awaiting approval</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {pendingVendors.map((vendor) => (
                <div
                  key={vendor.id}
                  className="tnt-card border-amber-200 hover:border-amber-300 transition-all"
                >
                  <div className="flex items-start gap-3 mb-4">
                    <div className="w-12 h-12 rounded-xl bg-amber-50 flex items-center justify-center shrink-0">
                      <Store className="w-6 h-6 text-amber-600" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <h4 className="font-semibold text-[#111827] truncate">{vendor.name}</h4>
                      <StatusBadge type="vendor_type" status={vendor.vendor_type} />
                    </div>
                    <StatusBadge type="vendor" status="pending" />
                  </div>

                  <div className="space-y-1.5 mb-4 text-xs text-[#9CA3AF]">
                    <div className="flex justify-between">
                      <span>Phone</span>
                      <span className="text-[#111827] font-mono">{vendor.phone}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Location</span>
                      <span className="text-[#111827]">{vendor.location || '—'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Applied</span>
                      <span className="text-[#111827]">{formatDate(vendor.created_at)}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => handleApprove(vendor.id)}
                      disabled={approvingId === vendor.id}
                      className="btn-success justify-center"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      Approve
                    </button>
                    <button
                      onClick={() => handleReject(vendor.id)}
                      disabled={approvingId === vendor.id}
                      className="btn-danger justify-center"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Rejected Tab */}
      {tab === 'rejected' && (
        <DataTable
          data={filteredVendors}
          columns={columns}
          loading={loading}
          onRowClick={(vendor) => navigate(`/vendors/${vendor.id}`)}
          emptyMessage="No rejected vendors"
        />
      )}
    </div>
  );
}