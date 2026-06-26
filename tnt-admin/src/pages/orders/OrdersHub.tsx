import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Filter, ShoppingBag, AlertTriangle, RefreshCw, Zap } from 'lucide-react';
import { type ColumnDef } from '@tanstack/react-table';
import toast from 'react-hot-toast';
import { DataTable } from '../../components/ui/DataTable';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { adminApi } from '../../api/admin';
import { formatOrderId, formatPaise, formatTimeAgo, formatDateTime } from '../../utils/format';
import { POLL_INTERVAL_ORDERS, ACTIVE_ORDER_STATUSES } from '../../utils/constants';
import type { Order, OrderStatus } from '../../types';
import { cn } from '../../utils/cn';

type OrdersTab = 'all' | 'live' | 'fraud';

export default function OrdersHub() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [tab, setTab] = useState<OrdersTab>('all');
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [statusFilter, setStatusFilter] = useState<OrderStatus | 'all'>('all');
  const [fraudOnly, setFraudOnly] = useState(false);
  const [flagging, setFlagging] = useState<number | null>(null);

  const fetchOrders = useCallback(async () => {
    try {
      const res = await adminApi.getAllOrders({ sort: 'newest' });
      setOrders(Array.isArray(res.data) ? res.data : []);
    } catch {
      // silent on poll failure
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, POLL_INTERVAL_ORDERS);
    return () => clearInterval(interval);
  }, [fetchOrders]);

  const handleFlagFraud = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setFlagging(id);
    try {
      await adminApi.flagOrderFraud(id);
      setOrders(prev => prev.map(o => o.id === id ? { ...o, fraud_flag: true } : o));
      toast.success(`Order ${formatOrderId(id)} flagged as fraud`);
    } catch {
      toast.error('Failed to flag order');
    } finally {
      setFlagging(null);
    }
  };

  const filteredOrders = orders.filter(o => {
    const matchSearch = !searchQuery ||
      formatOrderId(o.id).toLowerCase().includes(searchQuery.toLowerCase()) ||
      (o.user_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (o.vendor_name || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchStatus = statusFilter === 'all' || o.status === statusFilter;
    const matchFraud = !fraudOnly || o.fraud_flag;
    const matchTab = tab === 'all' ? true :
      tab === 'live' ? ACTIVE_ORDER_STATUSES.includes(o.status) :
      tab === 'fraud' ? o.fraud_flag : true;
    return matchSearch && matchStatus && matchFraud && matchTab;
  });

  const columns: ColumnDef<Order, unknown>[] = [
    {
      accessorKey: 'id',
      header: 'Order ID',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span className="font-mono text-[#E85D24] text-xs font-bold">
            {formatOrderId(row.original.id)}
          </span>
          {row.original.fraud_flag && (
            <span
              className="badge bg-red-500/20 text-red-400 border-red-500/30 text-[10px]"
              title={row.original.fraud_reason || 'Flagged as fraud'}
            >
              FRAUD
            </span>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'user_name',
      header: 'Student',
      cell: ({ row }) => (
        <span className="text-[#111827]">
          {row.original.user_name || `User #${row.original.user_id}`}
        </span>
      ),
    },
    {
      accessorKey: 'vendor_name',
      header: 'Vendor',
      cell: ({ row }) => (
        <span className="text-[#6B7280] text-xs">
          {row.original.vendor_name || `Vendor #${row.original.vendor_id}`}
        </span>
      ),
    },
    {
      id: 'items',
      header: 'Items',
      cell: ({ row }) => (
        <span className="text-xs text-[#6B7280]">
          {row.original.items?.length > 0 ? `${row.original.items.length} item(s)` : '—'}
        </span>
      ),
    },
    {
      accessorKey: 'total_amount',
      header: 'Amount',
      cell: ({ row }) => (
        <span className="font-mono text-sm font-medium">
          ₹{(row.original.total_amount / 100).toFixed(0)}
        </span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge type="order" status={row.original.status} />,
    },
    {
      accessorKey: 'created_at',
      header: 'Time',
      cell: ({ row }) => (
        <span className="text-xs text-[#6B7280] font-mono whitespace-nowrap">
          {formatTimeAgo(row.original.created_at)}
        </span>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          {!row.original.fraud_flag && (
            <button
              onClick={(e) => handleFlagFraud(row.original.id, e)}
              disabled={flagging === row.original.id}
              className="btn-ghost btn-sm text-red-400 hover:text-red-300 border-red-500/30"
              title="Flag as fraud"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      ),
    },
  ];

  const liveOrders = filteredOrders.filter(o => ACTIVE_ORDER_STATUSES.includes(o.status));
  const fraudOrders = filteredOrders.filter(o => o.fraud_flag);

  return (
    <div className="space-y-5">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Orders', value: orders.length, color: 'text-blue-500' },
          { label: 'Live (Active)', value: liveOrders.length, color: 'text-green-500' },
          { label: 'Fraud Flagged', value: fraudOrders.length, color: 'text-red-500' },
          { label: 'Revenue Today', value: `₹${(orders.reduce((a, o) => a + o.total_amount, 0) / 100).toFixed(0)}`, color: 'text-[#E85D24]' },
        ].map(stat => (
          <div key={stat.label} className="tnt-card-sm text-center">
            <p className={cn('text-xl font-bold font-mono', stat.color)}>{stat.value}</p>
            <p className="text-xs text-[#6B7280] mt-0.5">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl w-fit">
        {([
          { id: 'all', label: 'All Orders' },
          { id: 'live', label: `Live Feed (${liveOrders.length})` },
          { id: 'fraud', label: `Fraud Flagged (${fraudOrders.length})` },
        ] as const).map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`tab-btn ${tab === t.id ? 'active' : ''}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Filters (All tab only) */}
      {tab === 'all' && (
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6B7280]" />
            <input
              type="text"
              placeholder="Search order ID, student, vendor..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="tnt-input pl-9"
            />
          </div>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as OrderStatus | 'all')} className="tnt-select w-40">
            <option value="all">All Status</option>
            <option value="placed">Placed</option>
            <option value="confirmed">Confirmed</option>
            <option value="preparing">Preparing</option>
            <option value="ready">Ready</option>
            <option value="picked_up">Picked Up</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <label className="flex items-center gap-2 text-sm text-[#6B7280] cursor-pointer">
            <input
              type="checkbox"
              checked={fraudOnly}
              onChange={e => setFraudOnly(e.target.checked)}
              className="accent-[#E85D24]"
            />
            Fraud only
          </label>
          <button onClick={() => fetchOrders()} className="btn-ghost">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Live Feed — pulsing cards */}
      {tab === 'live' && (
        <div className="space-y-3">
          {liveOrders.length === 0 ? (
            <div className="tnt-card text-center py-12">
              <div className="w-2 h-2 rounded-full bg-green-400 mx-auto mb-3" />
              <p className="text-[#6B7280]">No active orders right now</p>
            </div>
          ) : (
            liveOrders.map(order => (
              <div
                key={order.id}
                onClick={() => navigate(`/orders/${order.id}`)}
                className="tnt-card cursor-pointer hover:border-[#E85D24]/40 transition-all"
              >
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
                    <div className="absolute inset-0 rounded-full bg-green-400 animate-ping opacity-50" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-[#E85D24] font-bold text-sm">
                        {formatOrderId(order.id)}
                      </span>
                      <StatusBadge type="order" status={order.status} />
                      {order.fraud_flag && (
                        <span className="badge bg-red-500/20 text-red-400 border-red-500/30 text-[10px]">FRAUD</span>
                      )}
                    </div>
                    <p className="text-xs text-[#4B5563] mt-0.5">
                      {order.user_name || `User #${order.user_id}`} → {order.vendor_name || `Vendor #${order.vendor_id}`}
                      {' '}• {order.items?.length || 0} item(s) • ₹{(order.total_amount / 100).toFixed(0)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-[#6B7280]">{formatTimeAgo(order.created_at)}</p>
                    {!order.fraud_flag && (
                      <button
                        onClick={(e) => handleFlagFraud(order.id, e)}
                        className="text-xs text-red-400 hover:text-red-300 mt-1 flex items-center gap-1"
                      >
                        <AlertTriangle className="w-3 h-3" /> Flag
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Fraud Flagged Tab */}
      {tab === 'fraud' && (
        <DataTable
          data={fraudOrders}
          columns={columns}
          loading={loading}
          onRowClick={order => navigate(`/orders/${order.id}`)}
          emptyMessage="No fraud-flagged orders"
        />
      )}

      {/* All Orders Table */}
      {tab === 'all' && (
        <DataTable
          data={filteredOrders}
          columns={columns}
          loading={loading}
          onRowClick={order => navigate(`/orders/${order.id}`)}
          emptyMessage="No orders found"
        />
      )}
    </div>
  );
}
