import React, { useEffect, useState } from 'react';
import { Store, User, Phone, Tag, Shield, Edit3, Save, X, Users, Plus, Trash2, ToggleLeft, ToggleRight } from 'lucide-react';
import toast from 'react-hot-toast';
import { vendorAuthApi } from '../../api/vendorAuth';
import type { VendorProfile, VendorStaff } from '../../api/vendorAuth';

export default function VendorProfilePage() {
  const [profile, setProfile] = useState<VendorProfile | null>(null);
  const [staff, setStaff] = useState<VendorStaff[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [formName, setFormName] = useState('');
  const [formCategory, setFormCategory] = useState('');
  const [showAddStaff, setShowAddStaff] = useState(false);
  const [staffForm, setStaffForm] = useState({ name: '', role: 'staff', phone: '', password: '' });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [profileRes, staffRes] = await Promise.all([
        vendorAuthApi.getProfile(),
        vendorAuthApi.listStaff(),
      ]);
      setProfile(profileRes.data);
      setStaff(staffRes.data);
      setFormName(profileRes.data.vendor_name);
      setFormCategory(profileRes.data.category || '');
    } catch {
      toast.error('Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async () => {
    try {
      const res = await vendorAuthApi.updateProfile({
        vendor_name: formName,
        category: formCategory || undefined,
      });
      setProfile(res.data);
      setEditing(false);
      toast.success('Profile updated');
    } catch {
      toast.error('Failed to update profile');
    }
  };

  const handleAddStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await vendorAuthApi.createStaff(staffForm);
      setStaff([res.data, ...staff]);
      setShowAddStaff(false);
      setStaffForm({ name: '', role: 'staff', phone: '', password: '' });
      toast.success('Staff added');
    } catch {
      toast.error('Failed to add staff');
    }
  };

  const handleToggleStaff = async (s: VendorStaff) => {
    try {
      const res = await vendorAuthApi.updateStaff(s.id, { is_active: !s.is_active });
      setStaff(staff.map((m) => (m.id === s.id ? res.data : m)));
      toast.success(`Staff ${res.data.is_active ? 'activated' : 'deactivated'}`);
    } catch {
      toast.error('Failed to update staff');
    }
  };

  const handleDeleteStaff = async (id: number) => {
    try {
      await vendorAuthApi.deleteStaff(id);
      setStaff(staff.filter((s) => s.id !== id));
      toast.success('Staff removed');
    } catch {
      toast.error('Failed to remove staff');
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-emerald-100 text-emerald-700';
      case 'pending': return 'bg-yellow-100 text-yellow-700';
      case 'suspended': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="text-center py-12 text-[#6B7280]">
        Unable to load vendor profile. Please try again.
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Profile Card */}
      <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 shadow-sm">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-emerald-100 flex items-center justify-center">
              <Store className="w-7 h-7 text-emerald-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[#111827]">{profile.vendor_name}</h2>
              <span className={`inline-block mt-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColor(profile.status)}`}>
                {profile.status}
              </span>
            </div>
          </div>
          <button
            onClick={() => setEditing(!editing)}
            className="p-2 rounded-lg hover:bg-gray-100 text-[#6B7280] transition-colors"
          >
            {editing ? <X className="w-5 h-5" /> : <Edit3 className="w-5 h-5" />}
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[#6B7280] uppercase tracking-wide">Vendor ID</label>
              <p className="mt-1 text-sm font-medium text-[#111827]">#{profile.vendor_id}</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-[#6B7280] uppercase tracking-wide">Category</label>
              {editing ? (
                <input
                  type="text"
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value)}
                  placeholder="food / stationery"
                  className="mt-1 w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-1.5 text-sm text-[#111827] focus:outline-none focus:border-emerald-500"
                />
              ) : (
                <p className="mt-1 text-sm font-medium text-[#111827]">{profile.category || '—'}</p>
              )}
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[#6B7280] uppercase tracking-wide">Owner</label>
              <p className="mt-1 text-sm font-medium text-[#111827]">{profile.owner_name || `User #${profile.owner_id}`}</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-[#6B7280] uppercase tracking-wide">Owner Phone</label>
              <p className="mt-1 text-sm font-medium text-[#111827]">{profile.owner_phone || '—'}</p>
            </div>
          </div>
        </div>

        {editing && (
          <div className="mt-6 pt-4 border-t border-[#E5E7EB] space-y-4">
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1">Vendor Name</label>
              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm text-[#111827] focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleUpdateProfile}
                className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors"
              >
                <Save className="w-4 h-4" /> Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="inline-flex items-center gap-2 bg-gray-100 hover:bg-gray-200 text-[#374151] font-medium py-2 px-4 rounded-lg text-sm transition-colors"
              >
                <X className="w-4 h-4" /> Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Staff Management */}
      <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Users className="w-5 h-5 text-[#6B7280]" />
            <h3 className="text-lg font-semibold text-[#111827]">Staff Members</h3>
            <span className="text-sm text-[#6B7280]">({staff.length})</span>
          </div>
          <button
            onClick={() => setShowAddStaff(!showAddStaff)}
            className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-3 rounded-lg text-sm transition-colors"
          >
            <Plus className="w-4 h-4" /> Add Staff
          </button>
        </div>

        {showAddStaff && (
          <form onSubmit={handleAddStaff} className="mb-6 p-4 bg-[#F9FAFB] rounded-xl border border-[#E5E7EB] space-y-3">
            <div className="grid md:grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Full Name"
                value={staffForm.name}
                onChange={(e) => setStaffForm({ ...staffForm, name: e.target.value })}
                className="bg-white border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                required
              />
              <input
                type="tel"
                placeholder="Phone Number"
                value={staffForm.phone}
                onChange={(e) => setStaffForm({ ...staffForm, phone: e.target.value.replace(/\D/g, '').slice(0, 15) })}
                className="bg-white border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                required
              />
              <select
                value={staffForm.role}
                onChange={(e) => setStaffForm({ ...staffForm, role: e.target.value })}
                className="bg-white border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
              >
                <option value="staff">Staff</option>
                <option value="manager">Manager</option>
              </select>
              <input
                type="password"
                placeholder="Password"
                value={staffForm.password}
                onChange={(e) => setStaffForm({ ...staffForm, password: e.target.value })}
                className="bg-white border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                required
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors">
                Add Staff
              </button>
              <button type="button" onClick={() => setShowAddStaff(false)} className="bg-gray-100 hover:bg-gray-200 text-[#374151] py-2 px-4 rounded-lg text-sm transition-colors">
                Cancel
              </button>
            </div>
          </form>
        )}

        {staff.length === 0 ? (
          <p className="text-sm text-[#9CA3AF] text-center py-6">No staff members yet.</p>
        ) : (
          <div className="space-y-2">
            {staff.map((s) => (
              <div key={s.id} className="flex items-center justify-between p-3 rounded-xl bg-[#F9FAFB] border border-[#E5E7EB]">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-emerald-100 flex items-center justify-center">
                    <User className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[#111827]">{s.name}</p>
                    <div className="flex items-center gap-2 text-xs text-[#6B7280]">
                      <span className="inline-flex items-center gap-1"><Phone className="w-3 h-3" />{s.phone}</span>
                      <span className="capitalize">· {s.role}</span>
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${s.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                        {s.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggleStaff(s)}
                    className="p-1.5 rounded-lg hover:bg-gray-200 text-[#6B7280] transition-colors"
                    title={s.is_active ? 'Deactivate' : 'Activate'}
                  >
                    {s.is_active ? <ToggleRight className="w-4 h-4 text-emerald-600" /> : <ToggleLeft className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => handleDeleteStaff(s.id)}
                    className="p-1.5 rounded-lg hover:bg-red-100 text-[#EF4444] transition-colors"
                    title="Remove"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
