import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, AlertTriangle, XCircle, CheckCircle, Clock,
  ShoppingBag, CreditCard, Wifi, WifiOff, Package,
  User, Store, IndianRupee,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { ordersApi } from '../../api/orders';
import { adminApi } from '../../api/admin';
import { useOrderWebSocket } from '../../hooks/useOrderWebSocket';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { formatOrderId, formatDateTime, formatTimeAgo, formatPaise } from '../../utils/format';
import { ACTIVE_ORDER_STATUSES } from '../../utils/constants';
import type { Order, OrderTimeline } from '../../types';
import { cn } from '../../utils/cn';

const ORDERED_STEPS = ['placed', 'confirmed', 'preparing', 'ready', 'picked'] as const;
const TERMINAL_STATES = ['cancelled', 'fraudflagged', 'fraud_flagged'] as const;

const STEP_LABELS: Record<string, string> = {
  placed: 'Order Placed',
  confirmed: 'Accepted by Vendor',
  preparing: 'Printing / Preparing',
  ready: 'Ready for Pickup',
  picked: 'Collected',
  cancelled: 'Cancelled',
  fraudflagged: 'Flagged for Review',
};

const STEP_DESCRIPTIONS: Record<string, string> = {
  placed: 'Order has been submitted',
  confirmed: 'The vendor accepted this order',
  preparing: 'Items are being prepared',
  ready: 'Available for QR pickup at the counter',
  picked: 'Successfully handed over to customer',
  cancelled: 'This order was cancelled',
  fraudflagged: 'This order has been flagged for review',
};

/** Map a timeline entry status string to one of the canonical step keys. */
function mapTimelineStatusToStep(status: string): string | null {
  const s = status.toLowerCase().replace(/_/g, '');
  if (s.includes('place')) return 'placed';
  if (s.includes('confirm')) return 'confirmed';
  if (s.includes('prepar')) return 'preparing';
  if (s.includes('read')) return 'ready';      // catches both "ready" and "ready_for_pickup"
  if (s.includes('pick') || s.includes('complet')) return 'picked';
  if (s.includes('cancel')) return 'cancelled';
  if (s.includes('fraud')) return 'fraudflagged';
  return null;
}

function OrderStatusStepper({
  currentStatus,
  timeline,
}: {
  currentStatus: string;
  timeline: OrderTimeline[];
}) {
  const status = currentStatus.toLowerCase();
  const isCancelled = status === 'cancelled';
  const isFlagged = status === 'fraudflagged' || status === 'fraud_flagged';
  const isTerminal = isCancelled || isFlagged;

  // Build timestamp map from real timeline data.
  // Backend returns { status, changed_at, actor }, frontend type expects { event, actor, timestamp }.
  const timestampMap: Record<string, string> = {};
  for (const entry of timeline) {
    const raw: any = entry;
    const eventText = raw.status ?? raw.event ?? '';
    const step = mapTimelineStatusToStep(eventText);
    const ts = raw.changed_at ?? raw.timestamp ?? '';
    if (step && ts) {
      // Keep earliest occurrence for each step
      if (!timestampMap[step]) timestampMap[step] = ts;
    }
  }

  const steps = isTerminal ? [...ORDERED_STEPS, status] : [...ORDERED_STEPS];
  const currentIndex = isTerminal
    ? steps.indexOf(status)
    : ORDERED_STEPS.indexOf(status as typeof ORDERED_STEPS[number]);

  const formatStepTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        month: 'short',
        day: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="relative">
      {steps.map((step, index) => {
        const isCompleted = index < currentIndex;
        const isCurrent = step === status;
        const isLast = index === steps.length - 1;
        const ts = timestampMap[step];

        /* ── Dot colour ─────────────────────────────────────────── */
        let dotRing = '';
        let dotBg = '';
        let connBg = '';
        let labelColor = '';

        if (isCurrent && isCancelled) {
          dotRing = 'ring-red-100';
          dotBg = 'var(--danger)';
          labelColor = 'var(--danger)';
        } else if (isCurrent && isFlagged) {
          dotRing = 'ring-amber-100';
          dotBg = 'var(--warning)';
          labelColor = 'var(--warning)';
        } else if (isCurrent) {
          dotRing = 'ring-[var(--primary-soft)]';
          dotBg = 'var(--primary)';
          labelColor = 'var(--primary)';
        } else if (isCompleted) {
          dotRing = 'ring-green-100';
          dotBg = 'var(--success)';
          labelColor = 'var(--text-primary)';
        } else {
          dotRing = 'ring-gray-100';
          dotBg = 'var(--border-default)';
          labelColor = 'var(--text-tertiary)';
        }

        if (isCompleted) connBg = 'var(--success)';
        else connBg = 'var(--border-default)';

        return (
          <div key={step} className="flex gap-4">
            {/* Dot column */}
            <div className="flex flex-col items-center">
              <div
                className="h-4 w-4 rounded-full ring-4 shrink-0 mt-0.5 transition-all"
                style={{ backgroundColor: dotBg, '--tw-ring-color': dotRing } as React.CSSProperties}
              />
              {!isLast && (
                <div
                  className="w-0.5 flex-1 min-h-[2rem] mt-1 transition-all"
                  style={{ backgroundColor: connBg }}
                />
              )}
            </div>

            {/* Content column */}
            <div className={cn('pb-6', isLast && 'pb-0')}>
              <p
                className="text-sm font-medium"
                style={{ color: isCurrent ? labelColor : labelColor, fontWeight: isCurrent ? 600 : undefined }}
              >
                {STEP_LABELS[step] ?? step.replace(/_/g, ' ')}
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                {STEP_DESCRIPTIONS[step] ?? ''}
              </p>
              {ts && (
                <p className="text-xs mt-1 font-mono" style={{ color: 'var(--text-tertiary)' }}>
                  {formatStepTime(ts)}
                </p>
              )}
              {isCurrent && !ts && (
                <span
                  className="inline-flex items-center gap-1 text-xs mt-1"
                  style={{ color: 'var(--primary)' }}
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full animate-pulse"
                    style={{ backgroundColor: 'var(--primary)' }}
                  />
                  In progress
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const orderId = Number(id);

  const [order, setOrder] = useState<Order | null>(null);
  const [timeline, setTimeline] = useState<OrderTimeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const isActive = order && ACTIVE_ORDER_STATUSES.includes(order.status);
  const { update: wsUpdate, connected: wsConnected } = useOrderWebSocket(isActive ? orderId : null);

  const fetchOrder = useCallback(async () => {
    setLoading(true);
    try {
      const [orderRes, timelineRes] = await Promise.allSettled([
        ordersApi.getById(orderId),
        ordersApi.getTimeline(orderId),
      ]);

      if (orderRes.status === 'fulfilled' && orderRes.value.data) {
        setOrder(orderRes.value.data);
      } else {
        toast.error('Order not found');
      }

      if (timelineRes.status === 'fulfilled') {
        setTimeline(Array.isArray(timelineRes.value.data) ? timelineRes.value.data : []);
      }
    } catch {
      toast.error('Failed to load order details');
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => { fetchOrder(); }, [fetchOrder]);

  useEffect(() => {
    if (wsUpdate && order) {
      setOrder(prev => prev ? { ...prev, status: wsUpdate.status } : null);
      // Refresh timeline when WS updates arrive so timestamps stay in sync
      fetchOrder();
    }
  }, [wsUpdate, order, fetchOrder]);

  const handleFlagFraud = async () => {
    setActionLoading(true);
    try {
      await adminApi.flagOrderFraud(orderId);
      setOrder(prev => prev ? { ...prev, fraud_flag: true } : null);
      toast.success('Order flagged as fraudulent');
    } catch { toast.error('Failed to flag order'); }
    finally { setActionLoading(false); }
  };

  const handleCancel = async () => {
    setActionLoading(true);
    try {
      await ordersApi.cancel(orderId);
      setOrder(prev => prev ? { ...prev, status: 'cancelled' } : null);
      toast.success('Order cancelled');
      fetchOrder();
    } catch { toast.error('Failed to cancel order'); }
    finally { setActionLoading(false); }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-10 w-40 rounded-lg" />
        <div className="skeleton h-48 rounded-xl" />
        <div className="grid grid-cols-2 gap-4">
          <div className="skeleton h-64 rounded-xl" />
          <div className="skeleton h-64 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="tnt-card text-center py-16">
        <p style={{ color: 'var(--text-tertiary)' }}>Order not found</p>
        <button onClick={() => navigate('/orders')} className="btn-primary mt-4">Back to Orders</button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <button onClick={() => navigate('/orders')} className="btn-ghost">
        <ArrowLeft className="w-4 h-4" /> All Orders
      </button>

      {/* Header */}
      <div className="tnt-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-2xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
                {formatOrderId(order.id)}
              </h2>
              <StatusBadge type="order" status={order.status} />
              {order.fraud_flag && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                  style={{ backgroundColor: 'rgba(239,68,68,0.08)', color: 'var(--danger)', border: '1px solid rgba(239,68,68,0.2)' }}
                >
                  ⚠ FRAUD FLAGGED
                </span>
              )}
              {isActive && (
                <div
                  className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium"
                  style={{
                    backgroundColor: wsConnected ? 'rgba(34,197,94,0.08)' : 'var(--bg-elevated)',
                    color: wsConnected ? 'var(--success)' : 'var(--text-secondary)',
                  }}
                >
                  {wsConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                  {wsConnected ? 'Live tracking' : 'Connecting...'}
                </div>
              )}
            </div>
            <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
              Placed {formatTimeAgo(order.created_at)} · {formatDateTime(order.created_at)}
            </p>
          </div>

          {/* Admin Actions */}
          <div className="flex flex-wrap gap-2">
            {!order.fraud_flag && (
              <button onClick={handleFlagFraud} disabled={actionLoading} className="btn-danger">
                <AlertTriangle className="w-4 h-4" /> Flag Fraud
              </button>
            )}
            {ACTIVE_ORDER_STATUSES.includes(order.status) && (
              <button onClick={handleCancel} disabled={actionLoading} className="btn-danger">
                <XCircle className="w-4 h-4" /> Force Cancel
              </button>
            )}
          </div>
        </div>

        {/* Quick Info Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5 pt-5" style={{ borderTop: '1px solid var(--border-default)' }}>
          {[
            { icon: User, label: 'Customer', value: order.user_name || `User #${order.user_id}` },
            { icon: Store, label: 'Vendor', value: order.vendor_name || `Vendor #${order.vendor_id}` },
            { icon: IndianRupee, label: 'Amount', value: `₹${(order.total_amount / 100).toFixed(2)}`, bold: true },
            { icon: CreditCard, label: 'Payment', value: order.payment_method || 'Razorpay' },
          ].map(({ icon: Icon, label, value, bold }) => (
            <div key={label} className="flex items-center gap-2 text-sm">
              <Icon className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</p>
                <p style={{ color: 'var(--text-primary)', fontWeight: bold ? 700 : 500, fontFamily: bold ? 'JetBrains Mono, monospace' : undefined }}>
                  {value}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Order Timeline */}
        <div className="tnt-card">
          <h3 className="text-sm font-semibold mb-5 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <Clock className="w-4 h-4" style={{ color: 'var(--primary)' }} />
            Order Timeline
          </h3>
          <OrderStatusStepper currentStatus={order.status} timeline={timeline} />
        </div>

        {/* Order Items + Payment */}
        <div className="space-y-4">
          {/* Items */}
          <div className="tnt-card">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <ShoppingBag className="w-4 h-4" style={{ color: 'var(--primary)' }} />
              Order Items
            </h3>
            {order.items?.length > 0 ? (
              <div className="space-y-2">
                {order.items.map((item) => (
                  <div key={item.id} className="flex items-center justify-between text-sm py-2"
                    style={{ borderBottom: '1px solid var(--border-default)' }}
                  >
                    <div>
                      <p style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{item.name}</p>
                      <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                        ₹{(item.unit_price / 100).toFixed(2)} × {item.quantity}
                      </p>
                    </div>
                    <span className="font-mono font-medium" style={{ color: 'var(--text-primary)' }}>
                      ₹{((item.unit_price * item.quantity) / 100).toFixed(2)}
                    </span>
                  </div>
                ))}
                <div className="flex items-center justify-between pt-2" style={{ borderTop: '1px solid var(--border-default)' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Total</span>
                  <span className="font-bold font-mono text-lg" style={{ color: 'var(--primary)' }}>
                    ₹{(order.total_amount / 100).toFixed(2)}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No items data available</p>
            )}
          </div>

          {/* Payment Info */}
          <div className="tnt-card">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <CreditCard className="w-4 h-4" style={{ color: 'var(--primary)' }} />
              Payment Details
            </h3>
            <div className="space-y-2 text-sm">
              {[
                { label: 'Amount', value: `₹${(order.total_amount / 100).toFixed(2)}` },
                { label: 'Method', value: order.payment_method || 'Razorpay' },
                { label: 'Payment ID', value: order.razorpay_payment_id || 'N/A' },
                { label: 'Fraud Flag', value: order.fraud_flag ? '⚠ Flagged' : 'Clean' },
                ...(order.fraud_flag && order.fraud_reason
                  ? [{ label: 'Fraud Reason', value: order.fraud_reason }]
                  : []),
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center py-1.5"
                  style={{ borderBottom: '1px solid var(--border-default)' }}
                >
                  <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                  <span
                    className="font-mono text-xs font-medium"
                    style={{
                      color: label === 'Fraud Reason' ? 'var(--danger)' :
                             label === 'Fraud Flag' && order.fraud_flag ? 'var(--danger)' : 'var(--text-primary)',
                      maxWidth: label === 'Fraud Reason' ? 200 : undefined,
                      textAlign: 'right' as const,
                    }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
