import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Store, MapPin, Phone, Star, ShoppingBag,
  Clock, CheckCircle, XCircle, Ban, Tag, Calendar,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { type ColumnDef } from '@tanstack/react-table';
import { DataTable } from '../../components/ui/DataTable';
import { StatusBadge } from '../../components/ui/StatusBadge';

import { adminApi } from '../../api/admin';
import { formatDate, formatRupees, formatTimeAgo } from '../../utils/format';
import type { Vendor, MenuItem, TimeSlot } from '../../types';
import { cn } from '../../utils/cn';

type DetailTab = 'menu' | 'slots' | 'orders' | 'feedback' | 'analytics';

export default function VendorDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const vendorId = Number(id);

  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<DetailTab>('menu');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchVendorData = useCallback(async () => {
    setLoading(true);
    try {
      const [vendorRes, menuRes, slotsRes] = await Promise.allSettled([
        adminApi.getVendorById(vendorId),
        adminApi.getVendorMenu(vendorId),
        adminApi.getVendorSlots(vendorId),
      ]);
      if (vendorRes.status === 'fulfilled') setVendor(vendorRes.value.data);
      if (menuRes.status === 'fulfilled') setMenu(Array.isArray(menuRes.value.data) ? menuRes.value.data : []);
      if (slotsRes.status === 'fulfilled') setSlots(Array.isArray(slotsRes.value.data) ? slotsRes.value.data : []);
    } catch {
      toast.error('Failed to load vendor details');
    } finally {
      setLoading(false);
    }
  }, [vendorId]);

  useEffect(() => { fetchVendorData(); }, [fetchVendorData]);

  const handleApprove = async () => {
    setActionLoading(true);
    try {
      await adminApi.approveVendor(vendorId);
      setVendor(prev => prev ? { ...prev, is_approved: true, is_active: true } : null);
      toast.success('Vendor approved');
    } catch { toast.error('Failed to approve'); }
    finally { setActionLoading(false); }
  };

  const handleReject = async () => {
    setActionLoading(true);
    try {
      await adminApi.rejectVendor(vendorId);
      setVendor(prev => prev ? { ...prev, is_approved: false } : null);
      toast.success('Vendor rejected');
    } catch { toast.error('Failed to reject'); }
    finally { setActionLoading(false); }
  };

  const menuColumns: ColumnDef<MenuItem, unknown>[] = [
    {
      accessorKey: 'name',
      header: 'Item',
      cell: ({ row }) => (
        <div>
          <p className="font-medium text-[#111827]">{row.original.name}</p>
          <p className="text-xs text-[#6B7280]">{row.original.category}</p>
        </div>
      ),
    },
    {
      accessorKey: 'price',
      header: 'Price',
      cell: ({ row }) => (
        <span className="font-mono text-sm font-medium">₹{(row.original.price / 100).toFixed(2)}</span>
      ),
    },
    {
      accessorKey: 'prep_time_minutes',
      header: 'Prep Time',
      cell: ({ row }) => (
        <div className="flex items-center gap-1 text-sm text-[#6B7280]">
          <Clock className="w-3.5 h-3.5" />
          {row.original.prep_time_minutes} min
        </div>
      ),
    },
    {
      accessorKey: 'is_available',
      header: 'Availability',
      cell: ({ row }) => (
        <StatusBadge
          type="active"
          status={row.original.is_available}
        />
      ),
    },
  ];

  const slotColumns: ColumnDef<TimeSlot, unknown>[] = [
    {
      accessorKey: 'start_time',
      header: 'Slot',
      cell: ({ row }) => (
        <span className="font-mono text-sm">
          {row.original.start_time} – {row.original.end_time}
        </span>
      ),
    },
    {
      accessorKey: 'capacity',
      header: 'Capacity',
      cell: ({ row }) => (
        <span className="font-mono">{row.original.capacity}</span>
      ),
    },
    {
      accessorKey: 'booked_count',
      header: 'Booked',
      cell: ({ row }) => {
        const utilization = (row.original.booked_count / row.original.capacity) * 100;
        return (
          <div className="flex items-center gap-2">
            <span className="font-mono">{row.original.booked_count}</span>
            <div className="w-16 bg-[#E5E7EB] rounded-full h-1.5 overflow-hidden">
              <div
                className={cn('h-full rounded-full', utilization >= 90 ? 'bg-red-400' : utilization >= 60 ? 'bg-amber-400' : 'bg-green-400')}
                style={{ width: `${Math.min(utilization, 100)}%` }}
              />
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => <StatusBadge type="active" status={row.original.is_active} />,
    },
  ];

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-10 w-40 rounded-lg" />
        <div className="skeleton h-32 rounded-xl" />
        <div className="skeleton h-64 rounded-xl" />
      </div>
    );
  }

  if (!vendor) {
    return (
      <div className="tnt-card text-center py-16">
        <p className="text-[#6B7280]">Vendor not found</p>
        <button onClick={() => navigate('/vendors')} className="btn-primary mt-4">
          Back to Vendors
        </button>
      </div>
    );
  }

  const tabs: { id: DetailTab; label: string }[] = [
    { id: 'menu', label: `Menu (${menu.length})` },
    { id: 'slots', label: `Time Slots (${slots.length})` },
    { id: 'orders', label: 'Orders' },
    { id: 'feedback', label: 'Feedback' },
    { id: 'analytics', label: 'Analytics' },
  ];

  return (
    <div className="space-y-5">
      {/* Back button */}
      <button onClick={() => navigate('/vendors')} className="btn-ghost">
        <ArrowLeft className="w-4 h-4" />
        All Vendors
      </button>

      {/* Header Card */}
      <div className="tnt-card">
        <div className="flex flex-wrap items-start gap-4">
          <div className="w-16 h-16 rounded-2xl bg-[#E85D24]/20 flex items-center justify-center shrink-0">
            <Store className="w-8 h-8 text-[#E85D24]" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <h2 className="text-2xl font-bold text-[#111827]">{vendor.name}</h2>
              <StatusBadge type="vendor_type" status={vendor.vendor_type} />
              <StatusBadge
                type="vendor"
                status={!vendor.is_approved ? 'pending' : !vendor.is_active ? 'inactive' : 'approved'}
              />
            </div>
            <div className="flex flex-wrap gap-4 text-sm text-[#6B7280]">
              <div className="flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5" />
                <span className="font-mono">{vendor.phone}</span>
              </div>
              {vendor.location && (
                <div className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5" />
                  {vendor.location}
                </div>
              )}
              {vendor.rating && (
                <div className="flex items-center gap-1.5 text-amber-400">
                  <Star className="w-3.5 h-3.5 fill-current" />
                  <span>{vendor.rating.toFixed(1)}</span>
                </div>
              )}
              <div className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                Joined {formatDate(vendor.created_at)}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 flex-wrap">
            {!vendor.is_approved && (
              <>
                <button onClick={handleApprove} disabled={actionLoading} className="btn-success">
                  <CheckCircle className="w-4 h-4" />
                  Approve
                </button>
                <button onClick={handleReject} disabled={actionLoading} className="btn-danger">
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
              </>
            )}
          </div>
        </div>

        {/* Quick stats */}
        <div className="grid grid-cols-3 gap-4 mt-5 pt-5 border-t border-[#E5E7EB]">
          <div className="text-center">
            <p className="text-lg font-bold text-[#111827] font-mono">{menu.length}</p>
            <p className="text-xs text-[#6B7280]">Menu Items</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-[#111827] font-mono">{slots.length}</p>
            <p className="text-xs text-[#6B7280]">Time Slots</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-[#111827] font-mono">
              {vendor.rating ? `⭐ ${vendor.rating.toFixed(1)}` : 'N/A'}
            </p>
            <p className="text-xs text-[#6B7280]">Avg Rating</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl w-fit flex-wrap">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'menu' && (
        <DataTable
          data={menu}
          columns={menuColumns}
          emptyMessage="No menu items"
        />
      )}
      {activeTab === 'slots' && (
        <DataTable
          data={slots}
          columns={slotColumns}
          emptyMessage="No time slots configured"
        />
      )}
      {activeTab === 'orders' && (
        <div className="tnt-card text-center py-12 text-[#6B7280]">
          <ShoppingBag className="w-10 h-10 mx-auto mb-3 opacity-50" />
          <p>Order history available in the Orders Hub</p>
          <button
            onClick={() => navigate(`/orders?vendor=${vendorId}`)}
            className="btn-primary mt-4"
          >
            View Orders
          </button>
        </div>
      )}
      {activeTab === 'feedback' && (
        <div className="tnt-card">
          <div className="flex items-center gap-3 mb-4">
            <Star className="w-5 h-5 text-amber-400" />
            <h3 className="text-sm font-semibold text-[#111827]">Vendor Feedback</h3>
          </div>
          {vendor.rating ? (
            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="text-5xl font-bold text-[#111827]">{vendor.rating.toFixed(1)}</p>
                <div className="flex gap-0.5 mt-1 justify-center">
                  {[1, 2, 3, 4, 5].map(s => (
                    <Star
                      key={s}
                      className={cn(
                        'w-4 h-4',
                        s <= Math.round(vendor.rating || 0) ? 'text-amber-400 fill-current' : 'text-[#E5E7EB]'
                      )}
                    />
                  ))}
                </div>
              </div>
              <div className="flex-1 space-y-1.5">
                {[5, 4, 3, 2, 1].map(star => {
                  const pct = star === 5 ? 65 : star === 4 ? 20 : star === 3 ? 10 : star === 2 ? 3 : 2;
                  return (
                    <div key={star} className="flex items-center gap-2 text-xs">
                      <span className="text-[#6B7280] w-4">{star}★</span>
                      <div className="flex-1 bg-[#E5E7EB] rounded-full h-1.5">
                        <div
                          className="bg-amber-400 h-full rounded-full"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <p className="text-[#6B7280] text-sm">No feedback data available</p>
          )}
        </div>
      )}
      {activeTab === 'analytics' && (
        <div className="tnt-card text-center py-12 text-[#6B7280]">
          <Tag className="w-10 h-10 mx-auto mb-3 opacity-50" />
          <p>Detailed analytics available in the AI Intelligence section</p>
          <button onClick={() => navigate('/ai')} className="btn-primary mt-4">
            View AI Analytics
          </button>
        </div>
      )}
    </div>
  );
}
