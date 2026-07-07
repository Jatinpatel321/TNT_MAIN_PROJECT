import React, { useState, useEffect } from 'react';
import { AlertOctagon, AlertTriangle, Info, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import { cn } from '../../utils/cn';

type Tab = 'overbooked' | 'duplicates' | 'warnings';

interface SlotConflict {
  slot_id: number;
  conflict_type: string;
  severity: string;
  start_time?: string;
  end_time?: string;
  vendor_id?: number;
  max_orders?: number;
  current_orders?: number;
  overflow?: number;
  fill_rate?: number;
  user_id?: number;
  booking_count?: number;
}

interface ConflictSummary {
  overbooked_slots: SlotConflict[];
  duplicate_bookings: SlotConflict[];
  capacity_warnings: SlotConflict[];
  totals: {
    critical: number;
    high: number;
    medium: number;
  };
}

const formatTime = (iso?: string) =>
  iso
    ? new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' })
    : '—';

export default function ConflictResolution() {
  const [activeTab, setActiveTab] = useState<Tab>('overbooked');
  const [data, setData] = useState<ConflictSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    setRefreshing(true);
    try {
      const res = await adminApi.getConflicts();
      setData(res.data);
    } catch {
      toast.error('Failed to load conflict data');
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const tabs = [
    { key: 'overbooked' as Tab, label: 'Overbooked Slots', icon: AlertOctagon, countKey: 'critical' as const },
    { key: 'duplicates' as Tab, label: 'Duplicate Bookings', icon: AlertTriangle, countKey: 'high' as const },
    { key: 'warnings' as Tab, label: 'Capacity Warnings', icon: Info, countKey: 'medium' as const },
  ];

  const getCurrentList = (): SlotConflict[] => {
    if (!data) return [];
    if (activeTab === 'overbooked') return data.overbooked_slots;
    if (activeTab === 'duplicates') return data.duplicate_bookings;
    return data.capacity_warnings;
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#111827]">Conflict Resolution</h2>
          <p className="text-sm text-[#6B7280] mt-1">
            Slot overbooking, duplicate entries, and capacity violations
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={refreshing}
          className="btn-ghost flex items-center gap-2"
        >
          <RefreshCw className={cn('w-4 h-4', refreshing && 'animate-spin')} />
          Refresh
        </button>
      </div>

      <div className="flex gap-2 border-b border-[#E5E7EB]">
        {tabs.map(({ key, label, icon: Icon, countKey }) => {
          const count = data?.totals?.[countKey] ?? 0;
          return (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors -mb-px',
                activeTab === key
                  ? 'border-[#4F46E5] text-[#4F46E5]'
                  : 'border-transparent text-[#6B7280] hover:text-[#111827]'
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
              {count > 0 && (
                <span className={cn(
                  'inline-flex items-center justify-center h-5 min-w-5 px-1.5 rounded-full text-xs font-bold text-white',
                  key === 'overbooked' ? 'bg-red-500' : key === 'duplicates' ? 'bg-amber-500' : 'bg-blue-400'
                )}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="tnt-card overflow-hidden p-0">
        {loading ? (
          <div className="p-10 flex justify-center">
            <div className="w-6 h-6 border-2 border-[#2E2E50] border-t-[#E85D24] rounded-full animate-spin" />
          </div>
        ) : getCurrentList().length === 0 ? (
          <div className="py-16 text-center text-sm text-[#6B7280]">
            ✓ No conflicts detected in this category.
          </div>
        ) : (
          <table className="tnt-table">
            <thead>
              <tr>
                {activeTab === 'overbooked' && (
                  <><th>Slot ID</th><th>Vendor</th><th>Start Time</th><th>End Time</th><th>Max</th><th>Booked</th><th>Overflow</th></>
                )}
                {activeTab === 'duplicates' && (
                  <><th>Slot ID</th><th>User ID</th><th>Duplicate Count</th></>
                )}
                {activeTab === 'warnings' && (
                  <><th>Slot ID</th><th>Vendor</th><th>Start Time</th><th>Fill Rate</th><th>Booked / Max</th></>
                )}
              </tr>
            </thead>
            <tbody>
              {getCurrentList().map((conflict, i) => (
                <tr key={i} className="hover:bg-[#F3F5F9]">
                  {activeTab === 'overbooked' && (
                    <>
                      <td className="font-mono text-sm">#{conflict.slot_id}</td>
                      <td className="text-sm text-[#4B5563]">#{conflict.vendor_id}</td>
                      <td className="text-sm">{formatTime(conflict.start_time)}</td>
                      <td className="text-sm">{formatTime(conflict.end_time)}</td>
                      <td className="text-sm">{conflict.max_orders}</td>
                      <td className="text-sm font-semibold text-red-600">{conflict.current_orders}</td>
                      <td>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-red-50 text-red-700">
                          +{conflict.overflow}
                        </span>
                      </td>
                    </>
                  )}
                  {activeTab === 'duplicates' && (
                    <>
                      <td className="font-mono text-sm">#{conflict.slot_id}</td>
                      <td className="font-mono text-sm">#{conflict.user_id}</td>
                      <td>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700">
                          {conflict.booking_count}× bookings
                        </span>
                      </td>
                    </>
                  )}
                  {activeTab === 'warnings' && (
                    <>
                      <td className="font-mono text-sm">#{conflict.slot_id}</td>
                      <td className="text-sm text-[#4B5563]">#{conflict.vendor_id}</td>
                      <td className="text-sm">{formatTime(conflict.start_time)}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-[#E5E7EB] rounded-full h-2">
                            <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${(conflict.fill_rate ?? 0) * 100}%` }} />
                          </div>
                          <span className="text-xs text-[#6B7280]">{Math.round((conflict.fill_rate ?? 0) * 100)}%</span>
                        </div>
                      </td>
                      <td className="text-sm">{conflict.current_orders} / {conflict.max_orders}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}