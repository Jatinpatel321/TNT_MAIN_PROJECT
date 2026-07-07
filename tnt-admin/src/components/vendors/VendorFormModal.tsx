import React, { useState } from 'react';
import { X, Store, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import type { Vendor, VendorType, VendorMeta } from '../../types';

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] as const;

interface Props {
  vendor?: Vendor | null; // present → edit mode
  onClose: () => void;
  onSaved: () => void;
}

type Hours = Record<string, { open: string; close: string; closed: boolean }>;

function initialHours(meta?: VendorMeta): Hours {
  const h: Hours = {};
  for (const d of DAYS) {
    const existing = meta?.operating_hours?.[d];
    h[d] = {
      open: existing?.open ?? '09:00',
      close: existing?.close ?? '18:00',
      closed: existing?.closed ?? false,
    };
  }
  return h;
}

export function VendorFormModal({ vendor, onClose, onSaved }: Props) {
  const isEdit = !!vendor;
  const meta = vendor?.vendor_meta ?? {};

  const [phone, setPhone] = useState(vendor?.phone ?? '');
  const [name, setName] = useState(vendor?.name ?? '');
  const [vendorType, setVendorType] = useState<VendorType>(vendor?.vendor_type ?? 'food');
  const [isApproved, setIsApproved] = useState(vendor?.is_approved ?? true);
  const [isActive, setIsActive] = useState(vendor?.is_active ?? true);
  const [stall, setStall] = useState(meta.stall ?? '');
  const [location, setLocation] = useState(meta.location ?? vendor?.location ?? '');
  const [businessName, setBusinessName] = useState(meta.business_name ?? '');
  const [email, setEmail] = useState(meta.email ?? '');
  const [description, setDescription] = useState(meta.description ?? '');
  const [slotDuration, setSlotDuration] = useState<string>(String(meta.slot_defaults?.slot_duration_minutes ?? 15));
  const [defaultCapacity, setDefaultCapacity] = useState<string>(String(meta.slot_defaults?.default_capacity ?? 20));
  const [openingTime, setOpeningTime] = useState(meta.slot_defaults?.opening_time ?? '09:00');
  const [closingTime, setClosingTime] = useState(meta.slot_defaults?.closing_time ?? '18:00');
  const [hours, setHours] = useState<Hours>(initialHours(meta));
  const [saving, setSaving] = useState(false);

  const setDay = (day: string, patch: Partial<Hours[string]>) =>
    setHours((prev) => ({ ...prev, [day]: { ...prev[day], ...patch } }));

  const buildPayload = () => ({
    name: name.trim(),
    vendor_type: vendorType,
    stall: stall.trim() || null,
    location: location.trim() || null,
    business_name: businessName.trim() || null,
    email: email.trim() || null,
    description: description.trim() || null,
    operating_hours: hours,
    slot_defaults: {
      slot_duration_minutes: Number(slotDuration) || 15,
      default_capacity: Number(defaultCapacity) || 20,
      opening_time: openingTime,
      closing_time: closingTime,
    },
  });

  const handleSubmit = async () => {
    if (!name.trim()) { toast.error('Name is required'); return; }
    if (!isEdit && !phone.trim()) { toast.error('Phone is required'); return; }
    setSaving(true);
    try {
      if (isEdit && vendor) {
        await adminApi.updateVendor(vendor.id, { ...buildPayload(), is_approved: isApproved, is_active: isActive });
        toast.success('Vendor updated');
      } else {
        await adminApi.createVendor({ phone: phone.trim(), is_approved: isApproved, ...buildPayload() });
        toast.success('Vendor created');
      }
      onSaved();
      onClose();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="tnt-card w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Store className="w-5 h-5 text-[#E85D24]" />
            <h2 className="text-lg font-bold text-[#111827]">{isEdit ? 'Edit Vendor' : 'Create Vendor'}</h2>
          </div>
          <button onClick={onClose} className="btn-ghost btn-sm"><X className="w-4 h-4" /></button>
        </div>

        <div className="space-y-4">
          {/* Identity */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">Phone {!isEdit && <span className="text-red-500">*</span>}</label>
              <input className="tnt-input" value={phone} disabled={isEdit}
                onChange={(e) => setPhone(e.target.value)} placeholder="10-digit phone" />
            </div>
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">Vendor Name <span className="text-red-500">*</span></label>
              <input className="tnt-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Stall name" />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">Vendor Type</label>
              <select className="tnt-select" value={vendorType} onChange={(e) => setVendorType(e.target.value as VendorType)}>
                <option value="food">Food</option>
                <option value="stationery">Stationery</option>
                <option value="mixed">Mixed</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">Stall No.</label>
              <input className="tnt-input" value={stall} onChange={(e) => setStall(e.target.value)} placeholder="e.g. A-12" />
            </div>
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">Location</label>
              <input className="tnt-input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Block / Floor" />
            </div>
          </div>

          {/* Business metadata */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">Business Name</label>
              <input className="tnt-input" value={businessName} onChange={(e) => setBusinessName(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-[#6B7280] mb-1 block">Email</label>
              <input className="tnt-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="vendor@campus.edu" />
            </div>
          </div>
          <div>
            <label className="text-xs text-[#6B7280] mb-1 block">Description</label>
            <textarea className="tnt-input" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>

          {/* Slot defaults */}
          <div>
            <h3 className="text-sm font-semibold text-[#374151] mb-2">Slot Defaults</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <label className="text-xs text-[#6B7280] mb-1 block">Slot mins</label>
                <input type="number" className="tnt-input" value={slotDuration} onChange={(e) => setSlotDuration(e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-[#6B7280] mb-1 block">Capacity</label>
                <input type="number" className="tnt-input" value={defaultCapacity} onChange={(e) => setDefaultCapacity(e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-[#6B7280] mb-1 block">Opens</label>
                <input type="time" className="tnt-input" value={openingTime} onChange={(e) => setOpeningTime(e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-[#6B7280] mb-1 block">Closes</label>
                <input type="time" className="tnt-input" value={closingTime} onChange={(e) => setClosingTime(e.target.value)} />
              </div>
            </div>
          </div>

          {/* Operating hours */}
          <div>
            <h3 className="text-sm font-semibold text-[#374151] mb-2">Operating Hours</h3>
            <div className="space-y-1.5">
              {DAYS.map((d) => (
                <div key={d} className="flex items-center gap-2">
                  <span className="w-24 text-xs capitalize text-[#4B5563]">{d}</span>
                  <input type="time" className="tnt-input w-28 text-sm" value={hours[d].open}
                    disabled={hours[d].closed} onChange={(e) => setDay(d, { open: e.target.value })} />
                  <span className="text-[#9CA3AF] text-xs">to</span>
                  <input type="time" className="tnt-input w-28 text-sm" value={hours[d].close}
                    disabled={hours[d].closed} onChange={(e) => setDay(d, { close: e.target.value })} />
                  <label className="flex items-center gap-1 text-xs text-[#6B7280] ml-2">
                    <input type="checkbox" checked={hours[d].closed} onChange={(e) => setDay(d, { closed: e.target.checked })} />
                    Closed
                  </label>
                </div>
              ))}
            </div>
          </div>

          {/* Status */}
          <div className="flex items-center gap-4 pt-1">
            <label className="flex items-center gap-2 text-sm text-[#374151]">
              <input type="checkbox" checked={isApproved} onChange={(e) => setIsApproved(e.target.checked)} />
              Approved
            </label>
            {isEdit && (
              <label className="flex items-center gap-2 text-sm text-[#374151]">
                <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
                Active
              </label>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="btn-ghost">Cancel</button>
          <button onClick={handleSubmit} disabled={saving} className="btn-primary">
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            {isEdit ? 'Save Changes' : 'Create Vendor'}
          </button>
        </div>
      </div>
    </div>
  );
}
