import React, { useEffect, useState } from 'react';
import {
  Calendar,
  Clock,
  Settings,
  BarChart3,
  Plus,
  Trash2,
  Edit3,
  Save,
  X,
  Lock,
  Unlock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { slotsApi, type Slot, type SlotCreate, type SlotUpdate, type SlotAnalytics, type SlotCapacityRule, type SlotRule } from '../../api/slots';

type Tab = 'slots' | 'capacity' | 'rules' | 'analytics';

export default function SlotManagementPage() {
  const [activeTab, setActiveTab] = useState<Tab>('slots');
  const [slots, setSlots] = useState<Slot[]>([]);
  const [analytics, setAnalytics] = useState<SlotAnalytics | null>(null);
  const [capacityRules, setCapacityRules] = useState<SlotCapacityRule[]>([]);
  const [slotRules, setSlotRules] = useState<SlotRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [editingSlot, setEditingSlot] = useState<Slot | null>(null);

  const [slotForm, setSlotForm] = useState<SlotCreate>({
    start_time: '',
    end_time: '',
    max_orders: 10,
    slot_duration_minutes: undefined,
    is_peak_hour: false,
    is_faculty_priority: false,
    auto_block_enabled: false,
    dynamic_capacity: undefined,
    capacity_notes: '',
  });

  const [bulkForm, setBulkForm] = useState({
    start_date: '',
    end_date: '',
    interval_minutes: 60,
    max_orders: 10,
    is_peak_hour: false,
    is_faculty_priority: false,
    auto_block_enabled: false,
  });

  const [ruleForm, setRuleForm] = useState({
    rule_type: 'auto_block',
    rule_config: { enabled: true },
    is_enabled: true,
    priority: 0,
  });

  const [capacityForm, setCapacityForm] = useState({
    rule_name: '',
    day_of_week: undefined as number | undefined,
    start_hour: 9,
    end_hour: 17,
    base_capacity: 10,
    peak_capacity: undefined as number | undefined,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [slotsRes, analyticsRes, rulesRes, capacityRes] = await Promise.all([
        slotsApi.list(),
        slotsApi.analytics(),
        slotsApi.getRules(),
        slotsApi.getCapacityRules(),
      ]);
      setSlots(slotsRes.data);
      setAnalytics(analyticsRes.data);
      setSlotRules(rulesRes.data);
      setCapacityRules(capacityRes.data);
    } catch {
      toast.error('Failed to load slot data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSlot = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await slotsApi.create(slotForm);
      toast.success('Slot created successfully');
      setShowCreateModal(false);
      resetSlotForm();
      loadData();
    } catch {
      toast.error('Failed to create slot');
    }
  };

  const handleBulkCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await slotsApi.bulkCreate(bulkForm as any);
      toast.success('Slots created successfully');
      setShowBulkModal(false);
      resetBulkForm();
      loadData();
    } catch {
      toast.error('Failed to create slots');
    }
  };

  const handleUpdateSlot = async (slotId: number, data: SlotUpdate) => {
    try {
      await slotsApi.update(slotId, data);
      toast.success('Slot updated');
      setEditingSlot(null);
      loadData();
    } catch {
      toast.error('Failed to update slot');
    }
  };

  const handleDeleteSlot = async (slotId: number) => {
    if (!confirm('Are you sure you want to delete this slot?')) return;
    try {
      await slotsApi.delete(slotId);
      toast.success('Slot deleted');
      loadData();
    } catch {
      toast.error('Failed to delete slot');
    }
  };

  const handleToggleLock = async (slotId: number, isLocked: boolean) => {
    try {
      if (isLocked) {
        await slotsApi.unlock(slotId);
        toast.success('Slot unlocked');
      } else {
        await slotsApi.lock(slotId);
        toast.success('Slot locked');
      }
      loadData();
    } catch {
      toast.error('Failed to toggle lock');
    }
  };

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await slotsApi.createRule(ruleForm);
      toast.success('Rule created');
      setRuleForm({ rule_type: 'auto_block', rule_config: { enabled: true }, is_enabled: true, priority: 0 });
      loadData();
    } catch {
      toast.error('Failed to create rule');
    }
  };

  const handleCreateCapacityRule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await slotsApi.createCapacityRule({ ...capacityForm, is_active: true });
      toast.success('Capacity rule created');
      setCapacityForm({ rule_name: '', day_of_week: undefined, start_hour: 9, end_hour: 17, base_capacity: 10, peak_capacity: undefined });
      loadData();
    } catch {
      toast.error('Failed to create capacity rule');
    }
  };

  const handleDeleteRule = async (ruleId: number) => {
    try {
      await slotsApi.deleteRule(ruleId);
      toast.success('Rule deleted');
      loadData();
    } catch {
      toast.error('Failed to delete rule');
    }
  };

  const handleDeleteCapacityRule = async (ruleId: number) => {
    try {
      await slotsApi.deleteCapacityRule(ruleId);
      toast.success('Capacity rule deleted');
      loadData();
    } catch {
      toast.error('Failed to delete capacity rule');
    }
  };

  const resetSlotForm = () => {
    setSlotForm({
      start_time: '',
      end_time: '',
      max_orders: 10,
      slot_duration_minutes: undefined,
      is_peak_hour: false,
      is_faculty_priority: false,
      auto_block_enabled: false,
      dynamic_capacity: undefined,
      capacity_notes: '',
    });
  };

  const resetBulkForm = () => {
    setBulkForm({
      start_date: '',
      end_date: '',
      interval_minutes: 60,
      max_orders: 10,
      is_peak_hour: false,
      is_faculty_priority: false,
      auto_block_enabled: false,
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'available': return 'bg-emerald-100 text-emerald-700';
      case 'limited': return 'bg-yellow-100 text-yellow-700';
      case 'full': return 'bg-red-100 text-red-700';
      case 'blocked': return 'bg-gray-100 text-gray-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const formatDateTime = (dt: string) => {
    return new Date(dt).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#111827]">Slot Management</h1>
          <p className="text-sm text-[#6B7280] mt-1">Manage vendor slots, capacity rules, and automation</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowBulkModal(true)}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors"
          >
            <Calendar className="w-4 h-4" /> Bulk Create
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors"
          >
            <Plus className="w-4 h-4" /> Create Slot
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-[#E5E7EB]">
        <nav className="flex gap-6">
          {[
            { id: 'slots', label: 'Slots', icon: Calendar },
            { id: 'capacity', label: 'Capacity Rules', icon: Settings },
            { id: 'rules', label: 'Automation Rules', icon: Zap },
            { id: 'analytics', label: 'Analytics', icon: BarChart3 },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as Tab)}
              className={`flex items-center gap-2 pb-3 px-1 border-b-2 transition-colors ${
                activeTab === id
                  ? 'border-emerald-500 text-emerald-600'
                  : 'border-transparent text-[#6B7280] hover:text-[#111827]'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="text-sm font-medium">{label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Slots Tab */}
      {activeTab === 'slots' && (
        <div className="space-y-4">
          {slots.length === 0 ? (
            <div className="text-center py-12 text-[#6B7280]">
              No slots found. Create your first slot to get started.
            </div>
          ) : (
            <div className="grid gap-4">
              {slots.map((slot) => (
                <div key={slot.id} className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-sm">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <Clock className="w-5 h-5 text-[#6B7280]" />
                        <div>
                          <h3 className="font-semibold text-[#111827]">
                            {formatDateTime(slot.start_time)} - {formatDateTime(slot.end_time)}
                          </h3>
                          <p className="text-xs text-[#6B7280] mt-0.5">Slot #{slot.id}</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                        <div>
                          <p className="text-xs text-[#6B7280] uppercase tracking-wide">Capacity</p>
                          <p className="text-sm font-medium text-[#111827] mt-1">
                            {slot.current_orders} / {slot.max_orders}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-[#6B7280] uppercase tracking-wide">Status</p>
                          <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(slot.status)}`}>
                            {slot.status}
                          </span>
                        </div>
                        <div>
                          <p className="text-xs text-[#6B7280] uppercase tracking-wide">Load</p>
                          <p className="text-sm font-medium text-[#111827] mt-1">{slot.load_label}</p>
                        </div>
                        <div>
                          <p className="text-xs text-[#6B7280] uppercase tracking-wide">Est. Wait</p>
                          <p className="text-sm font-medium text-[#111827] mt-1">{slot.estimated_wait} min</p>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {slot.is_peak_hour && (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-orange-100 text-orange-700 text-xs font-medium">
                            <TrendingUp className="w-3 h-3" /> Peak Hour
                          </span>
                        )}
                        {slot.is_faculty_priority && (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-purple-100 text-purple-700 text-xs font-medium">
                            <Users className="w-3 h-3" /> Faculty Priority
                          </span>
                        )}
                        {slot.auto_block_enabled && (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-blue-100 text-blue-700 text-xs font-medium">
                            <Lock className="w-3 h-3" /> Auto-Block
                          </span>
                        )}
                        {slot.is_locked && (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-red-100 text-red-700 text-xs font-medium">
                            <Lock className="w-3 h-3" /> Locked
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 ml-4">
                      <button
                        onClick={() => handleToggleLock(slot.id, slot.is_locked)}
                        className={`p-2 rounded-lg transition-colors ${
                          slot.is_locked
                            ? 'bg-red-100 hover:bg-red-200 text-red-600'
                            : 'bg-gray-100 hover:bg-gray-200 text-[#6B7280]'
                        }`}
                        title={slot.is_locked ? 'Unlock' : 'Lock'}
                      >
                        {slot.is_locked ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={() => setEditingSlot(slot)}
                        className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-[#6B7280] transition-colors"
                        title="Edit"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteSlot(slot.id)}
                        className="p-2 rounded-lg bg-red-100 hover:bg-red-200 text-red-600 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Capacity Rules Tab */}
      {activeTab === 'capacity' && (
        <div className="space-y-6">
          <form onSubmit={handleCreateCapacityRule} className="bg-white rounded-xl border border-[#E5E7EB] p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-[#111827] mb-4">Create Capacity Rule</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1">Rule Name</label>
                <input
                  type="text"
                  value={capacityForm.rule_name}
                  onChange={(e) => setCapacityForm({ ...capacityForm, rule_name: e.target.value })}
                  className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1">Day of Week (0-6, optional)</label>
                <input
                  type="number"
                  min="0"
                  max="6"
                  value={capacityForm.day_of_week ?? ''}
                  onChange={(e) => setCapacityForm({ ...capacityForm, day_of_week: e.target.value ? parseInt(e.target.value) : undefined })}
                  className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  placeholder="0=Mon, 6=Sun"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1">Start Hour</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={capacityForm.start_hour}
                  onChange={(e) => setCapacityForm({ ...capacityForm, start_hour: parseInt(e.target.value) })}
                  className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1">End Hour</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={capacityForm.end_hour}
                  onChange={(e) => setCapacityForm({ ...capacityForm, end_hour: parseInt(e.target.value) })}
                  className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1">Base Capacity</label>
                <input
                  type="number"
                  min="1"
                  value={capacityForm.base_capacity}
                  onChange={(e) => setCapacityForm({ ...capacityForm, base_capacity: parseInt(e.target.value) })}
                  className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1">Peak Capacity (optional)</label>
                <input
                  type="number"
                  min="1"
                  value={capacityForm.peak_capacity ?? ''}
                  onChange={(e) => setCapacityForm({ ...capacityForm, peak_capacity: e.target.value ? parseInt(e.target.value) : undefined })}
                  className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>
            <button type="submit" className="mt-4 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors">
              Create Rule
            </button>
          </form>

          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-[#111827]">Existing Rules</h3>
            {capacityRules.length === 0 ? (
              <p className="text-sm text-[#9CA3AF] text-center py-6">No capacity rules configured.</p>
            ) : (
              capacityRules.map((rule) => (
                <div key={rule.id} className="bg-white rounded-xl border border-[#E5E7EB] p-4 flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-[#111827]">{rule.rule_name}</h4>
                    <p className="text-xs text-[#6B7280] mt-1">
                      Hours: {rule.start_hour}:00 - {rule.end_hour}:00 | Base: {rule.base_capacity}
                      {rule.peak_capacity && ` | Peak: ${rule.peak_capacity}`}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteCapacityRule(rule.id)}
                    className="p-2 rounded-lg bg-red-100 hover:bg-red-200 text-red-600 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Rules Tab */}
      {activeTab === 'rules' && (
        <div className="space-y-6">
          <form onSubmit={handleCreateRule} className="bg-white rounded-xl border border-[#E5E7EB] p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-[#111827] mb-4">Create Automation Rule</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1">Rule Type</label>
                <select
                  value={ruleForm.rule_type}
                  onChange={(e) => setRuleForm({ ...ruleForm, rule_type: e.target.value })}
                  className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                >
                  <option value="auto_block">Auto Block</option>
                  <option value="faculty_priority">Faculty Priority</option>
                  <option value="peak_hour">Peak Hour</option>
                  <option value="duration">Duration</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1">Priority</label>
                <input
                  type="number"
                  value={ruleForm.priority}
                  onChange={(e) => setRuleForm({ ...ruleForm, priority: parseInt(e.target.value) })}
                  className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>
            <div className="mt-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={ruleForm.is_enabled}
                  onChange={(e) => setRuleForm({ ...ruleForm, is_enabled: e.target.checked })}
                  className="rounded border-[#E5E7EB] text-emerald-600 focus:ring-emerald-500"
                />
                <span className="text-sm text-[#374151]">Enabled</span>
              </label>
            </div>
            <button type="submit" className="mt-4 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors">
              Create Rule
            </button>
          </form>

          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-[#111827]">Existing Rules</h3>
            {slotRules.length === 0 ? (
              <p className="text-sm text-[#9CA3AF] text-center py-6">No automation rules configured.</p>
            ) : (
              slotRules.map((rule) => (
                <div key={rule.id} className="bg-white rounded-xl border border-[#E5E7EB] p-4 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-[#111827]">{rule.rule_type}</h4>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${rule.is_enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                        {rule.is_enabled ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <p className="text-xs text-[#6B7280] mt-1">Priority: {rule.priority}</p>
                  </div>
                  <button
                    onClick={() => handleDeleteRule(rule.id)}
                    className="p-2 rounded-lg bg-red-100 hover:bg-red-200 text-red-600 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && analytics && (
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <Calendar className="w-5 h-5 text-emerald-600" />
              <p className="text-sm text-[#6B7280]">Total Slots</p>
            </div>
            <p className="text-2xl font-bold text-[#111827]">{analytics.total_slots}</p>
          </div>
          <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <CheckCircle className="w-5 h-5 text-emerald-600" />
              <p className="text-sm text-[#6B7280]">Available</p>
            </div>
            <p className="text-2xl font-bold text-[#111827]">{analytics.available_slots}</p>
          </div>
          <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <AlertTriangle className="w-5 h-5 text-yellow-600" />
              <p className="text-sm text-[#6B7280]">Limited</p>
            </div>
            <p className="text-2xl font-bold text-[#111827]">{analytics.limited_slots}</p>
          </div>
          <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <XCircle className="w-5 h-5 text-red-600" />
              <p className="text-sm text-[#6B7280]">Full</p>
            </div>
            <p className="text-2xl font-bold text-[#111827]">{analytics.full_slots}</p>
          </div>
          <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <BarChart3 className="w-5 h-5 text-blue-600" />
              <p className="text-sm text-[#6B7280]">Avg Utilization</p>
            </div>
            <p className="text-2xl font-bold text-[#111827]">{analytics.avg_utilization}%</p>
          </div>
          <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <Users className="w-5 h-5 text-purple-600" />
              <p className="text-sm text-[#6B7280]">Total Bookings</p>
            </div>
            <p className="text-2xl font-bold text-[#111827]">{analytics.total_bookings}</p>
          </div>
          <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="w-5 h-5 text-orange-600" />
              <p className="text-sm text-[#6B7280]">Peak Hour Slots</p>
            </div>
            <p className="text-2xl font-bold text-[#111827]">{analytics.peak_hour_slots}</p>
          </div>
          <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <Users className="w-5 h-5 text-indigo-600" />
              <p className="text-sm text-[#6B7280]">Faculty Priority</p>
            </div>
            <p className="text-2xl font-bold text-[#111827]">{analytics.faculty_priority_slots}</p>
          </div>
        </div>
      )}

      {/* Create Slot Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-[#111827]">Create New Slot</h2>
              <button onClick={() => setShowCreateModal(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateSlot} className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1">Start Time</label>
                  <input
                    type="datetime-local"
                    value={slotForm.start_time}
                    onChange={(e) => setSlotForm({ ...slotForm, start_time: e.target.value })}
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1">End Time</label>
                  <input
                    type="datetime-local"
                    value={slotForm.end_time}
                    onChange={(e) => setSlotForm({ ...slotForm, end_time: e.target.value })}
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1">Max Orders</label>
                  <input
                    type="number"
                    min="1"
                    value={slotForm.max_orders}
                    onChange={(e) => setSlotForm({ ...slotForm, max_orders: parseInt(e.target.value) })}
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1">Duration (minutes, optional)</label>
                  <input
                    type="number"
                    min="1"
                    value={slotForm.slot_duration_minutes ?? ''}
                    onChange={(e) => setSlotForm({ ...slotForm, slot_duration_minutes: e.target.value ? parseInt(e.target.value) : undefined })}
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={slotForm.is_peak_hour}
                    onChange={(e) => setSlotForm({ ...slotForm, is_peak_hour: e.target.checked })}
                    className="rounded border-[#E5E7EB] text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-sm text-[#374151]">Peak Hour Slot</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={slotForm.is_faculty_priority}
                    onChange={(e) => setSlotForm({ ...slotForm, is_faculty_priority: e.target.checked })}
                    className="rounded border-[#E5E7EB] text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-sm text-[#374151]">Faculty Priority</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={slotForm.auto_block_enabled}
                    onChange={(e) => setSlotForm({ ...slotForm, auto_block_enabled: e.target.checked })}
                    className="rounded border-[#E5E7EB] text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-sm text-[#374151]">Auto-Block When Full</span>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1">Capacity Notes (optional)</label>
                <textarea
                  value={slotForm.capacity_notes}
                  onChange={(e) => setSlotForm({ ...slotForm, capacity_notes: e.target.value })}
                  className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  rows={2}
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors">
                  Create Slot
                </button>
                <button type="button" onClick={() => setShowCreateModal(false)} className="bg-gray-100 hover:bg-gray-200 text-[#374151] py-2 px-4 rounded-lg text-sm transition-colors">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bulk Create Modal */}
      {showBulkModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-2xl w-full">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-[#111827]">Bulk Create Slots</h2>
              <button onClick={() => setShowBulkModal(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleBulkCreate} className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1">Start Date</label>
                  <input
                    type="datetime-local"
                    value={bulkForm.start_date}
                    onChange={(e) => setBulkForm({ ...bulkForm, start_date: e.target.value })}
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1">End Date</label>
                  <input
                    type="datetime-local"
                    value={bulkForm.end_date}
                    onChange={(e) => setBulkForm({ ...bulkForm, end_date: e.target.value })}
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1">Interval (minutes)</label>
                  <input
                    type="number"
                    min="10"
                    step="10"
                    value={bulkForm.interval_minutes}
                    onChange={(e) => setBulkForm({ ...bulkForm, interval_minutes: parseInt(e.target.value) })}
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1">Max Orders Per Slot</label>
                  <input
                    type="number"
                    min="1"
                    value={bulkForm.max_orders}
                    onChange={(e) => setBulkForm({ ...bulkForm, max_orders: parseInt(e.target.value) })}
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={bulkForm.is_peak_hour}
                    onChange={(e) => setBulkForm({ ...bulkForm, is_peak_hour: e.target.checked })}
                    className="rounded border-[#E5E7EB] text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-sm text-[#374151]">Mark as Peak Hour</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={bulkForm.is_faculty_priority}
                    onChange={(e) => setBulkForm({ ...bulkForm, is_faculty_priority: e.target.checked })}
                    className="rounded border-[#E5E7EB] text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-sm text-[#374151]">Faculty Priority</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={bulkForm.auto_block_enabled}
                    onChange={(e) => setBulkForm({ ...bulkForm, auto_block_enabled: e.target.checked })}
                    className="rounded border-[#E5E7EB] text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-sm text-[#374151]">Auto-Block When Full</span>
                </label>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors">
                  Create Slots
                </button>
                <button type="button" onClick={() => setShowBulkModal(false)} className="bg-gray-100 hover:bg-gray-200 text-[#374151] py-2 px-4 rounded-lg text-sm transition-colors">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Slot Modal */}
      {editingSlot && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-2xl w-full">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-[#111827]">Edit Slot #{editingSlot.id}</h2>
              <button onClick={() => setEditingSlot(null)} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleUpdateSlot(editingSlot.id, {
                  max_orders: editingSlot.max_orders,
                  status: editingSlot.status,
                  is_locked: editingSlot.is_locked,
                  slot_duration_minutes: editingSlot.slot_duration_minutes,
                  is_peak_hour: editingSlot.is_peak_hour,
                  is_faculty_priority: editingSlot.is_faculty_priority,
                  auto_block_enabled: editingSlot.auto_block_enabled,
                  dynamic_capacity: editingSlot.dynamic_capacity,
                  capacity_notes: editingSlot.capacity_notes,
                });
              }}
              className="space-y-4"
            >
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1">Max Orders</label>
                  <input
                    type="number"
                    min="1"
                    value={editingSlot.max_orders}
                    onChange={(e) => setEditingSlot({ ...editingSlot, max_orders: parseInt(e.target.value) })}
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1">Status</label>
                  <select
                    value={editingSlot.status}
                    onChange={(e) => setEditingSlot({ ...editingSlot, status: e.target.value as Slot['status'] })}
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  >
                    <option value="available">Available</option>
                    <option value="limited">Limited</option>
                    <option value="full">Full</option>
                    <option value="blocked">Blocked</option>
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editingSlot.is_peak_hour}
                    onChange={(e) => setEditingSlot({ ...editingSlot, is_peak_hour: e.target.checked })}
                    className="rounded border-[#E5E7EB] text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-sm text-[#374151]">Peak Hour</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editingSlot.is_faculty_priority}
                    onChange={(e) => setEditingSlot({ ...editingSlot, is_faculty_priority: e.target.checked })}
                    className="rounded border-[#E5E7EB] text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-sm text-[#374151]">Faculty Priority</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editingSlot.auto_block_enabled}
                    onChange={(e) => setEditingSlot({ ...editingSlot, auto_block_enabled: e.target.checked })}
                    className="rounded border-[#E5E7EB] text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-sm text-[#374151]">Auto-Block</span>
                </label>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors">
                  Save Changes
                </button>
                <button type="button" onClick={() => setEditingSlot(null)} className="bg-gray-100 hover:bg-gray-200 text-[#374151] py-2 px-4 rounded-lg text-sm transition-colors">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}