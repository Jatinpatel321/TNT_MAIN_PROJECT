import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Gift, Clock, Plus, Edit2, Trash2, X, RefreshCw, Zap } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { type ColumnDef } from '@tanstack/react-table';
import toast from 'react-hot-toast';
import { DataTable } from '../../components/ui/DataTable';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { rewardsApi } from '../../api/rewards';
import { formatDate } from '../../utils/format';
import { generateVoucherCode } from '../../utils/format';
import type { Voucher } from '../../types';
import { cn } from '../../utils/cn';

const voucherSchema = z.object({
  code: z.string().min(4, 'Code must be at least 4 characters').max(20),
  discount_type: z.enum(['flat', 'percent']),
  discount_value: z.number().min(1).max(100),
  expiry_date: z.string().min(1, 'Expiry date required'),
  max_redemptions: z.number().int().min(1),
});

type VoucherFormData = z.infer<typeof voucherSchema>;

export default function VoucherManager() {
  const navigate = useNavigate();
  const location = useLocation();

  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editVoucher, setEditVoucher] = useState<Voucher | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Voucher | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm<VoucherFormData>({
    resolver: zodResolver(voucherSchema),
    defaultValues: {
      code: '',
      discount_type: 'flat',
      discount_value: 50,
      max_redemptions: 100,
    },
  });

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await rewardsApi.getVouchers();
      setVouchers(Array.isArray(res.data) ? res.data : []);
    } catch { toast.error('Failed to load vouchers'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const openCreate = () => {
    setEditVoucher(null);
    reset({ code: '', discount_type: 'flat', discount_value: 50, max_redemptions: 100 });
    setModalOpen(true);
  };

  const openEdit = (voucher: Voucher) => {
    setEditVoucher(voucher);
    reset({
      code: voucher.code,
      discount_type: voucher.discount_type,
      discount_value: voucher.discount_value,
      expiry_date: voucher.expiry_date.split('T')[0],
      max_redemptions: voucher.max_redemptions,
    });
    setModalOpen(true);
  };

  const onSubmit = async (data: VoucherFormData) => {
    setSubmitting(true);
    try {
      if (editVoucher) {
        const res = await rewardsApi.updateVoucher(editVoucher.id, data);
        setVouchers(prev => prev.map(v => v.id === editVoucher.id ? res.data : v));
        toast.success('Voucher updated');
      } else {
        const res = await rewardsApi.createVoucher(data);
        setVouchers(prev => [res.data, ...prev]);
        toast.success('Voucher created');
      }
      setModalOpen(false);
    } catch { toast.error('Failed to save voucher'); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async (voucher: Voucher) => {
    try {
      await rewardsApi.deleteVoucher(voucher.id);
      setVouchers(prev => prev.filter(v => v.id !== voucher.id));
      setDeleteConfirm(null);
      toast.success('Voucher deleted');
    } catch { toast.error('Failed to delete voucher'); }
  };

  const columns: ColumnDef<Voucher, unknown>[] = [
    {
      accessorKey: 'code',
      header: 'Code',
      cell: ({ row }) => (
        <span className="font-mono font-bold text-[#E85D24] text-sm tracking-wide">
          {row.original.code}
        </span>
      ),
    },
    {
      accessorKey: 'discount_type',
      header: 'Discount',
      cell: ({ row }) => (
        <span className="font-mono text-sm text-[#111827]">
          {row.original.discount_type === 'flat'
            ? `₹${row.original.discount_value}`
            : `${row.original.discount_value}%`}
          <span className="text-xs text-[#6B7280] ml-1">
            ({row.original.discount_type})
          </span>
        </span>
      ),
    },
    {
      accessorKey: 'expiry_date',
      header: 'Expires',
      cell: ({ row }) => (
        <span className="text-xs font-mono text-[#6B7280]">{formatDate(row.original.expiry_date)}</span>
      ),
    },
    {
      id: 'redemptions',
      header: 'Redeemed',
      cell: ({ row }) => {
        const pct = (row.original.redemption_count / row.original.max_redemptions) * 100;
        return (
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-[#111827]">
              {row.original.redemption_count}/{row.original.max_redemptions}
            </span>
            <div className="w-12 bg-[#E5E7EB] rounded-full h-1.5">
              <div
                className={cn('h-full rounded-full', pct >= 90 ? 'bg-red-400' : pct >= 60 ? 'bg-amber-400' : 'bg-green-400')}
                style={{ width: `${Math.min(pct, 100)}%` }}
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
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <button onClick={(e) => { e.stopPropagation(); openEdit(row.original); }} className="btn-ghost btn-sm">
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); setDeleteConfirm(row.original); }}
            className="btn-ghost btn-sm text-red-400 border-red-500/30"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
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

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Vouchers', value: vouchers.length, color: 'text-[#E85D24]' },
          { label: 'Active', value: vouchers.filter(v => v.is_active).length, color: 'text-green-500' },
          { label: 'Total Redeemed', value: vouchers.reduce((a, v) => a + v.redemption_count, 0), color: 'text-blue-500' },
          { label: 'Expired', value: vouchers.filter(v => new Date(v.expiry_date) < new Date()).length, color: 'text-red-500' },
        ].map(stat => (
          <div key={stat.label} className="tnt-card-sm text-center">
            <p className={cn('text-2xl font-bold font-mono', stat.color)}>{stat.value}</p>
            <p className="text-xs text-[#6B7280] mt-0.5">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Header + Create button */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#111827]">Vouchers</h2>
        <div className="flex gap-2">
          <button onClick={fetch} className="btn-ghost"><RefreshCw className="w-4 h-4" /></button>
          <button onClick={openCreate} className="btn-primary">
            <Plus className="w-4 h-4" /> Create Voucher
          </button>
        </div>
      </div>

      <DataTable
        data={vouchers}
        columns={columns}
        loading={loading}
        emptyMessage="No vouchers yet — create your first one!"
      />

      {/* Create/Edit Modal */}
      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold text-[#111827]">
                {editVoucher ? 'Edit Voucher' : 'Create Voucher'}
              </h3>
              <button onClick={() => setModalOpen(false)} className="btn-ghost btn-sm">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Code */}
              <div>
                <label className="tnt-label">Voucher Code</label>
                <div className="flex gap-2">
                  <input {...register('code')} className="tnt-input flex-1" placeholder="TNT2024XYZ" />
                  <button
                    type="button"
                    onClick={() => setValue('code', generateVoucherCode())}
                    className="btn-ghost shrink-0"
                  >
                    <Zap className="w-4 h-4" /> Auto
                  </button>
                </div>
                {errors.code && <p className="text-red-400 text-xs mt-1">{errors.code.message}</p>}
              </div>

              {/* Discount Type + Value */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="tnt-label">Discount Type</label>
                  <select {...register('discount_type')} className="tnt-select">
                    <option value="flat">Flat (₹)</option>
                    <option value="percent">Percentage (%)</option>
                  </select>
                </div>
                <div>
                  <label className="tnt-label">
                    Value ({watch('discount_type') === 'flat' ? '₹' : '%'})
                  </label>
                  <input
                    {...register('discount_value', { valueAsNumber: true })}
                    type="number"
                    className="tnt-input"
                    min={1}
                    max={watch('discount_type') === 'percent' ? 100 : undefined}
                  />
                  {errors.discount_value && (
                    <p className="text-red-400 text-xs mt-1">{errors.discount_value.message}</p>
                  )}
                </div>
              </div>

              {/* Expiry + Max Redemptions */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="tnt-label">Expiry Date</label>
                  <input {...register('expiry_date')} type="date" className="tnt-input" />
                  {errors.expiry_date && (
                    <p className="text-red-400 text-xs mt-1">{errors.expiry_date.message}</p>
                  )}
                </div>
                <div>
                  <label className="tnt-label">Max Redemptions</label>
                  <input
                    {...register('max_redemptions', { valueAsNumber: true })}
                    type="number"
                    className="tnt-input"
                    min={1}
                  />
                  {errors.max_redemptions && (
                    <p className="text-red-400 text-xs mt-1">{errors.max_redemptions.message}</p>
                  )}
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setModalOpen(false)} className="btn-ghost flex-1 justify-center">
                  Cancel
                </button>
                <button type="submit" disabled={submitting} className="btn-primary flex-1 justify-center">
                  {submitting ? 'Saving...' : editVoucher ? 'Update' : 'Create Voucher'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteConfirm && (
        <div className="modal-overlay">
          <div className="modal-content max-w-sm">
            <h3 className="text-lg font-semibold text-[#111827] mb-2">Delete Voucher?</h3>
            <p className="text-sm text-[#6B7280] mb-5">
              Voucher <span className="font-mono text-[#E85D24]">{deleteConfirm.code}</span> will be permanently deleted.
            </p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="btn-ghost flex-1 justify-center">Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="btn-danger flex-1 justify-center">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
