import React, { useState, useEffect, useCallback } from 'react';
import { Search, Users, Ban, CheckCircle, X, Phone, Calendar, ChevronLeft, ChevronRight, GraduationCap, BookOpen, Store, Shield } from 'lucide-react';
import toast from 'react-hot-toast';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { adminApi } from '../../api/admin';
import { formatDate } from '../../utils/format';
import { cn } from '../../utils/cn';

interface AdminUser {
  id: number;
  name: string | null;
  full_name: string | null;
  phone: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface UserListResponse {
  users: AdminUser[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  role_summary: Record<string, number>;
}

const ROLES = [
  { value: 'student', label: 'Students', icon: GraduationCap },
  { value: 'faculty', label: 'Faculty', icon: BookOpen },
  { value: 'vendor', label: 'Vendors', icon: Store },
  { value: 'admin', label: 'Admins', icon: Shield },
];

const ROLE_COLORS: Record<string, string> = {
  student: 'bg-blue-50 text-blue-700 border-blue-200',
  faculty: 'bg-purple-50 text-purple-700 border-purple-200',
  vendor: 'bg-amber-50 text-amber-700 border-amber-200',
  admin: 'bg-red-50 text-red-700 border-red-200',
};

export default function UserManagement() {
  const [data, setData] = useState(null as UserListResponse | null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [selectedUser, setSelectedUser] = useState(null as AdminUser | null);
  const [confirmBlock, setConfirmBlock] = useState(null as AdminUser | null);
  const [toggling, setToggling] = useState(null as number | null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);
  const [changingRole, setChangingRole] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [roleFilter, statusFilter]);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 20 };
      if (debouncedSearch) params.search = debouncedSearch;
      if (roleFilter) params.role = roleFilter;
      if (statusFilter !== 'all') params.is_active = statusFilter === 'active';

      const res = await adminApi.getUsers(params);
      setData(res.data);
    } catch {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, roleFilter, statusFilter]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const handleToggleUser = async (user: AdminUser) => {
    setToggling(user.id);
    try {
      await adminApi.updateUserStatus(user.id, !user.is_active);
      toast.success(user.is_active ? 'User blocked' : 'User unblocked');
      fetchUsers();
      if (selectedUser?.id === user.id) {
        setSelectedUser(prev => prev ? { ...prev, is_active: !prev.is_active } : null);
      }
    } catch {
      toast.error('Failed to update user status');
    } finally {
      setToggling(null);
      setConfirmBlock(null);
    }
  };

  const displayName = (user: AdminUser) => user.full_name || user.name || `User #${user.id}`;

  const toggleSelect = (id: number) => setSelectedIds(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const bulkAction = async (action: 'block' | 'unblock') => {
    if (selectedIds.size === 0) { toast.error('Select users first'); return; }
    setBulkBusy(true);
    try {
      const res = await adminApi.bulkUserAction(Array.from(selectedIds), action);
      toast.success(`${action === 'block' ? 'Blocked' : 'Unblocked'} ${res.data?.changed_count ?? 0} users`);
      setSelectedIds(new Set());
      fetchUsers();
    } catch { toast.error('Bulk action failed'); }
    finally { setBulkBusy(false); }
  };

  const changeRole = async (user: AdminUser, role: string) => {
    if (role === user.role) return;
    setChangingRole(true);
    try {
      await adminApi.changeUserRole(user.id, role);
      toast.success(`Role changed to ${role}`);
      setSelectedUser(prev => prev ? { ...prev, role } : null);
      fetchUsers();
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Failed to change role'); }
    finally { setChangingRole(false); }
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-[#111827]">User Management</h2>
        <p className="text-sm text-[#6B7280] mt-1">
          {data ? `${data.total.toLocaleString()} registered users` : 'Loading...'}
        </p>
      </div>

      {data?.role_summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {ROLES.map(r => {
            const Icon = r.icon;
            const count = data.role_summary[r.value] ?? 0;
            return (
              <button
                key={r.value}
                onClick={() => setRoleFilter(prev => prev === r.value ? '' : r.value)}
                className={cn(
                  'flex items-center gap-3 rounded-xl border p-3 text-left transition',
                  roleFilter === r.value
                    ? 'border-[#4F46E5] bg-indigo-50'
                    : 'border-[#E5E7EB] bg-white hover:border-[#4F46E5]'
                )}
              >
                <Icon className="h-5 w-5 text-[#6B7280] shrink-0" />
                <div>
                  <p className="text-xs text-[#6B7280]">{r.label}</p>
                  <p className="text-lg font-semibold text-[#111827]">{count.toLocaleString()}</p>
                </div>
              </button>
            );
          })}
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[220px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
          <input
            type="text"
            placeholder="Search by name, phone, ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="tnt-input pl-9"
          />
        </div>
        <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)} className="tnt-select w-36">
          <option value="">All Roles</option>
          <option value="student">Student</option>
          <option value="faculty">Faculty</option>
          <option value="vendor">Vendor</option>
          <option value="admin">Admin</option>
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="tnt-select w-36">
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="blocked">Blocked</option>
        </select>
      </div>

      {selectedIds.size > 0 && (
        <div className="flex items-center justify-between p-3 bg-indigo-50 border border-indigo-200 rounded-xl">
          <span className="text-sm font-medium text-[#4F46E5]">{selectedIds.size} selected</span>
          <div className="flex gap-2">
            <button onClick={() => bulkAction('unblock')} disabled={bulkBusy} className="btn-success btn-sm">
              <CheckCircle className="w-3.5 h-3.5" /> Unblock
            </button>
            <button onClick={() => bulkAction('block')} disabled={bulkBusy} className="btn-danger btn-sm">
              <Ban className="w-3.5 h-3.5" /> Block
            </button>
            <button onClick={() => setSelectedIds(new Set())} className="btn-ghost btn-sm">Clear</button>
          </div>
        </div>
      )}

      <div className="tnt-card overflow-hidden p-0">
        {loading ? (
          <div className="p-10 flex justify-center">
            <div className="w-6 h-6 border-2 border-[#2E2E50] border-t-[#E85D24] rounded-full animate-spin" />
          </div>
        ) : data?.users.length === 0 ? (
          <div className="py-16 text-center text-sm text-[#6B7280]">
            No users match the current filters.
          </div>
        ) : (
          <table className="tnt-table">
            <thead>
              <tr>
                <th className="w-8">
                  <input
                    type="checkbox"
                    aria-label="Select all on page"
                    checked={!!data?.users.length && data.users.every(u => selectedIds.has(u.id))}
                    onChange={(e) => {
                      const pageIds = data?.users.map(u => u.id) ?? [];
                      setSelectedIds(prev => {
                        const next = new Set(prev);
                        if (e.target.checked) pageIds.forEach(i => next.add(i));
                        else pageIds.forEach(i => next.delete(i));
                        return next;
                      });
                    }}
                  />
                </th>
                <th>User</th>
                <th>Phone</th>
                <th>Role</th>
                <th>Joined</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data?.users.map((user: AdminUser) => (
                <tr key={user.id} onClick={() => setSelectedUser(user)} className="cursor-pointer">
                  <td onClick={(e: any) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      aria-label={`Select ${displayName(user)}`}
                      checked={selectedIds.has(user.id)}
                      onChange={() => toggleSelect(user.id)}
                    />
                  </td>
                  <td>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-indigo-50 flex items-center justify-center text-[#4F46E5] font-bold text-sm shrink-0">
                        {(displayName(user).charAt(0) || '#').toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-[#111827]">{displayName(user)}</p>
                        <p className="text-xs text-[#9CA3AF] font-mono">#{user.id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="text-sm text-[#4B5563] font-mono">{user.phone}</td>
                  <td>
                    <span className={cn(
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize border',
                      ROLE_COLORS[user.role] || 'bg-gray-50 text-gray-700 border-gray-200'
                    )}>
                      {user.role}
                    </span>
                  </td>
                  <td className="text-sm text-[#6B7280]">{formatDate(user.created_at)}</td>
                  <td><StatusBadge type="active" status={user.is_active} /></td>
                  <td>
                    <button
                      onClick={(e: any) => { e.stopPropagation(); setConfirmBlock(user); }}
                      disabled={toggling === user.id}
                      className={cn(user.is_active ? 'btn-danger' : 'btn-success', 'btn-sm')}
                    >
                      {user.is_active ? (
                        <><Ban className="w-3.5 h-3.5" />Block</>
                      ) : (
                        <><CheckCircle className="w-3.5 h-3.5" />Unblock</>
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-[#6B7280]">
            Showing <span className="font-medium text-[#111827]">{(page - 1) * 20 + 1}–{Math.min(page * 20, data.total)}</span> of{' '}
            <span className="font-medium text-[#111827]">{data.total.toLocaleString()}</span>
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p: number) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg border border-[#E5E7EB] hover:bg-[#F3F5F9] disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm text-[#6B7280]">{page} / {data.total_pages}</span>
            <button
              onClick={() => setPage((p: number) => Math.min(data.total_pages, p + 1))}
              disabled={page === data.total_pages}
              className="p-2 rounded-lg border border-[#E5E7EB] hover:bg-[#F3F5F9] disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {selectedUser && (
        <>
          <div className="fixed inset-0 bg-black/40 z-40" onClick={() => setSelectedUser(null)} />
          <div className="slide-over">
            <div className="flex items-center justify-between p-5 border-b border-[#E5E7EB]">
              <h2 className="text-lg font-semibold text-[#111827]">User Profile</h2>
              <button onClick={() => setSelectedUser(null)} className="btn-ghost btn-sm">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 space-y-5">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-orange-50 flex items-center justify-center text-[#E85D24] font-bold text-2xl">
                  {displayName(selectedUser).charAt(0).toUpperCase()}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-[#111827]">{displayName(selectedUser)}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={cn(
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize border',
                      ROLE_COLORS[selectedUser.role] || 'bg-gray-50 text-gray-700 border-gray-200'
                    )}>
                      {selectedUser.role}
                    </span>
                    <StatusBadge type="active" status={selectedUser.is_active} />
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-3 text-sm">
                  <Phone className="w-4 h-4 text-[#9CA3AF]" />
                  <span className="font-mono text-[#111827]">{selectedUser.phone}</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <Calendar className="w-4 h-4 text-[#9CA3AF]" />
                  <span className="text-[#4B5563]">Joined {formatDate(selectedUser.created_at)}</span>
                </div>
              </div>

              {/* Role management */}
              <div className="pt-2 border-t border-[#E5E7EB]">
                <label className="text-xs text-[#6B7280] mb-1 block">Role</label>
                <select
                  className="tnt-select w-full"
                  aria-label="User role"
                  value={selectedUser.role}
                  disabled={changingRole}
                  onChange={(e) => changeRole(selectedUser, e.target.value)}
                >
                  {['student', 'faculty', 'vendor', 'staff', 'admin', 'super_admin'].map(r => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
                <p className="text-[11px] text-[#9CA3AF] mt-1">Changing a role updates the user's platform permissions immediately.</p>
              </div>

              <button
                onClick={() => setConfirmBlock(selectedUser)}
                disabled={toggling === selectedUser.id}
                className={cn('w-full justify-center', selectedUser.is_active ? 'btn-danger' : 'btn-success')}
              >
                {selectedUser.is_active ? (
                  <><Ban className="w-4 h-4" />Block User</>
                ) : (
                  <><CheckCircle className="w-4 h-4" />Unblock User</>
                )}
              </button>
            </div>
          </div>
        </>
      )}

      {confirmBlock && (
        <div className="modal-overlay">
          <div className="modal-content max-w-sm">
            <h3 className="text-lg font-semibold text-[#111827] mb-2">
              {confirmBlock.is_active ? 'Block User?' : 'Unblock User?'}
            </h3>
            <p className="text-sm text-[#4B5563] mb-5">
              {confirmBlock.is_active
                ? `${displayName(confirmBlock)} will be immediately denied access on their next API call.`
                : `${displayName(confirmBlock)} will regain access to the TNT platform.`}
            </p>
            <div className="flex gap-3">
              <button onClick={() => setConfirmBlock(null)} className="btn-ghost flex-1 justify-center">
                Cancel
              </button>
              <button
                onClick={() => handleToggleUser(confirmBlock)}
                disabled={toggling === confirmBlock.id}
                className={cn('flex-1 justify-center', confirmBlock.is_active ? 'btn-danger' : 'btn-success')}
              >
                {confirmBlock.is_active ? 'Block' : 'Unblock'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}