import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import {Text} from 'react-native-paper';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {useFocusEffect} from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import type {RootStackParamList} from '../../types/navigation';
import type {Order, OrderHistoryItem, Vendor} from '../../types/models';
import {Screen} from '../../components/Screen';
import {GradientButton} from '../../components/GradientButton';
import {OrderStatusCard} from '../../components/OrderStatusCard';
import {ETABox} from '../../components/ETABox';
import {OrderTimeline} from '../../components/OrderTimeline';
import {
  getMyOrders,
  getOrderEta,
  getOrderTimeline,
  generateOrderQr,
  getVendorOrderDetail,
  cancelOrder,
  reorderOrder,
  isActiveOrder,
  isTerminalOrder,
  ORDER_STATUS_LABELS,
  type OrderDetail,
  type OrderEtaResponse,
} from '../../services/orderService';
import {getVendors} from '../../services/vendorService';
import {getSlots} from '../../services/slotService';
import {toApiError} from '../../services/apiClient';
import {useOrderWebSocket} from '../../hooks/useOrderWebSocket';

type Props = NativeStackScreenProps<RootStackParamList, 'OrderTracking'>;

const POLL_INTERVAL_MS = 8000; // 8-second polling fallback

export function OrderTrackingScreen({route, navigation}: Props) {
  const {orderId} = route.params;

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [order, setOrder] = useState<Order | null>(null);
  const [timeline, setTimeline] = useState<OrderHistoryItem[]>([]);
  const [eta, setEta] = useState<OrderEtaResponse | null>(null);
  const [vendorMap, setVendorMap] = useState<Record<number, Vendor>>({});
  const [slots, setSlots] = useState<any[]>([]);
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [reordering, setReordering] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isTerminalRef = useRef(false);

  // ── Load auth token ──────────────────────────────────────────────────
  useEffect(() => {
    AsyncStorage.getItem('access_token').then(setToken).catch(() => {});
  }, []);

  // ── Load data (memoized with useCallback so it's stable for polling) ─
  const loadData = useCallback(
    async (isRefresh = false) => {
      try {
        if (!isRefresh) setLoading(true);
        const [orders, timelineRes, etaRes, slotsRes, food, stationery] =
          await Promise.all([
            getMyOrders(),
            getOrderTimeline(orderId),
            getOrderEta(orderId),
            getSlots(),
            getVendors('food'),
            getVendors('stationery'),
          ]);

        const foundOrder = orders.find(o => o.id === orderId) ?? null;
        setOrder(foundOrder);
        setTimeline(timelineRes);
        setEta(etaRes);
        setSlots(slotsRes.slots ?? slotsRes);
        const map: Record<number, Vendor> = {};
        [...food, ...stationery].forEach(v => {
          map[v.id] = v;
        });
        setVendorMap(map);

        if (foundOrder && isTerminalOrder(foundOrder.status)) {
          isTerminalRef.current = true;
        }

        try {
          const d = await getVendorOrderDetail(orderId);
          setDetail(d);
        } catch (_) {}
      } catch (e) {
        if (!isRefresh)
          Alert.alert('Failed to load order', toApiError(e).message);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [orderId],
  );

  // ── Load data on mount AND when screen regains focus ─────────────────
  useFocusEffect(
    useCallback(() => {
      let active = true;

      const run = async () => {
        try {
          await loadData();
        } catch (_) {
          // handled in loadData
        }
      };
      run();

      return () => {
        active = false;
      };
    }, [loadData]),
  );

  // ── Polling fallback ─────────────────────────────────────────────────
  // Starts when screen is focused and order is active.
  // Stops when: screen loses focus, order reaches terminal state,
  // or WebSocket is connected.
  const startPolling = useCallback(() => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    if (isTerminalRef.current) return;

    pollTimerRef.current = setInterval(() => {
      if (isTerminalRef.current) {
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        return;
      }
      loadData(true);
    }, POLL_INTERVAL_MS);
  }, [loadData]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  // ── WebSocket event handler ──────────────────────────────────────────
  const handleWSEvent = useCallback(
    (event: {event: string; data: any}) => {
      const {event: eventType, data} = event;

      switch (eventType) {
        case 'status_change':
          setOrder(prev =>
            prev
              ? {
                  ...prev,
                  status: data.new_status,
                  eta_minutes:
                    data.eta_minutes ?? prev.eta_minutes,
                }
              : prev,
          );
          // Reload timeline to get full history
          getOrderTimeline(orderId)
            .then(setTimeline)
            .catch(() => {});
          if (data.new_status && isTerminalOrder(data.new_status)) {
            isTerminalRef.current = true;
          }
          break;

        case 'eta_update':
          setEta(prev =>
            prev
              ? {
                  ...prev,
                  estimated_ready_at: data.eta_minutes
                    ? `${data.eta_minutes} min`
                    : prev.estimated_ready_at,
                  is_delayed: data.is_delayed,
                }
              : null,
          );
          setOrder(prev =>
            prev
              ? {
                  ...prev,
                  eta_minutes: data.eta_minutes ?? prev.eta_minutes,
                }
              : prev,
          );
          break;

        case 'pickup_confirmed':
          setOrder(prev => (prev ? {...prev, status: 'picked'} : prev));
          isTerminalRef.current = true;
          break;

        case 'status':
          // Initial snapshot
          if (data.status) {
            setOrder(prev =>
              prev
                ? {
                    ...prev,
                    status: data.status,
                    eta_minutes:
                      data.eta_minutes ?? prev.eta_minutes,
                  }
                : prev,
            );
          }
          break;
      }
    },
    [orderId],
  );

  // ── Connect WebSocket ────────────────────────────────────────────────
  const {isConnected: wsConnected} = useOrderWebSocket(
    orderId,
    token,
    handleWSEvent,
  );

  // ── Manage polling based on WS connection state ──────────────────────
  useEffect(() => {
    if (wsConnected) {
      // WebSocket is active — stop polling
      stopPolling();
    } else {
      // No WebSocket — start polling fallback
      startPolling();
    }

    return stopPolling;
  }, [wsConnected, startPolling, stopPolling]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadData(true);
  }, [loadData]);

  // ── Derived state ────────────────────────────────────────────────────
  const isActive = useMemo(() => {
    const statusKey = (order?.status ?? '').toLowerCase();
    return isActiveOrder(statusKey);
  }, [order]);

  const isTerminal = useMemo(() => {
    const statusKey = (order?.status ?? '').toLowerCase();
    return isTerminalOrder(statusKey);
  }, [order]);

  const vendorName = useMemo(() => {
    if (order && vendorMap[order.vendor_id])
      return (
        vendorMap[order.vendor_id].name ?? `Vendor #${order.vendor_id}`
      );
    if (order)
      return order.vendor_name ?? `Vendor #${order.vendor_id}`;
    return 'Vendor';
  }, [order, vendorMap]);

  const orderType = useMemo(() => {
    if (order?.booking_type === 'combined') return 'combined' as const;
    if (order && vendorMap[order.vendor_id]) {
      return vendorMap[order.vendor_id].vendor_type === 'stationery'
        ? 'stationery'
        : 'food';
    }
    return 'food';
  }, [order, vendorMap]);

  const status = useMemo(() => {
    if (timeline.length) return timeline[timeline.length - 1].status;
    return order?.status ?? 'placed';
  }, [timeline, order]);

  const slotWindow = useMemo(() => {
    if (!order) return null;
    const slot = slots.find(s => s.id === order.slot_id);
    if (!slot) return null;
    const start = new Date(slot.start_time).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
    const end = new Date(slot.end_time).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
    return `${start} – ${end}`;
  }, [order, slots]);

  const items: OrderDetail['items'] = detail?.items?.length
    ? detail.items
    : (order?.items?.map(i => ({
        name: i.name,
        quantity: i.quantity,
        price_at_time: i.price_at_time,
        line_total: i.price_at_time * i.quantity,
      })) ?? []);

  const totalAmount = detail?.total_amount ?? order?.total_amount ?? null;
  const totalRupees =
    typeof totalAmount === 'number'
      ? totalAmount < 100
        ? Number(totalAmount)
        : Number(totalAmount) / 100
      : null;

  const statusKey = (status || '').toLowerCase();
  const active = isActiveOrder(statusKey);
  const terminal = isTerminalOrder(statusKey);
  const canCancel = active && statusKey !== 'cancelled';
  const canReorder = statusKey === 'picked' || statusKey === 'completed';
  const canShowQr = statusKey === 'ready' || statusKey === 'ready_for_pickup';
  const canRate = statusKey === 'picked' || statusKey === 'completed';

  const onQr = useCallback(async () => {
    try {
      const res = await generateOrderQr(orderId);
      navigation.navigate('QR', {qrCode: res.qr_code, orderId});
    } catch (e) {
      Alert.alert('QR failed', toApiError(e).message);
    }
  }, [orderId, navigation]);

  const onCancel = useCallback(() => {
    Alert.alert(
      'Cancel Order',
      'Are you sure you want to cancel this order?',
      [
        {text: 'No', style: 'cancel'},
        {
          text: 'Yes, Cancel',
          style: 'destructive',
          onPress: async () => {
            try {
              setCancelling(true);
              await cancelOrder(orderId);
              Alert.alert('Cancelled', 'Your order has been cancelled.', [
                {text: 'OK', onPress: () => navigation.goBack()},
              ]);
            } catch (e) {
              Alert.alert('Cancel failed', toApiError(e).message);
            } finally {
              setCancelling(false);
            }
          },
        },
      ],
    );
  }, [orderId, navigation]);

  const onReorder = useCallback(async () => {
    try {
      setReordering(true);
      const res = await reorderOrder(orderId);
      Alert.alert(
        'Reorder Placed',
        `New order #${res.order_id} has been placed.`,
        [
          {
            text: 'Track Order',
            onPress: () =>
              navigation.replace('OrderTracking', {orderId: res.order_id}),
          },
          {text: 'OK'},
        ],
      );
    } catch (e) {
      Alert.alert('Reorder failed', toApiError(e).message);
    } finally {
      setReordering(false);
    }
  }, [orderId, navigation]);

  const onRate = useCallback(() => {
    navigation.navigate('Feedback', {
      orderId,
      vendorName:
        vendorName !== `Vendor #${order?.vendor_id}` ? vendorName : null,
    });
  }, [navigation, orderId, vendorName, order]);

  return (
    <ScrollView
      style={styles.scroll}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          colors={['#059669']}
          tintColor="#059669"
        />
      }>
      <Screen scroll={false}>
        <View style={styles.header}>
          <Text style={styles.title}>Order #{orderId}</Text>
          <View style={styles.headerRight}>
            <Text style={styles.sub}>
              {ORDER_STATUS_LABELS[statusKey] ?? status}
            </Text>
            {wsConnected && (
              <View style={styles.liveBadge}>
                <Text style={styles.liveBadgeText}>🟢 Live</Text>
              </View>
            )}
          </View>
        </View>

        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#059669" />
          </View>
        ) : (
          <>
            {!order ? (
              <View style={styles.center}>
                <Text style={styles.emptyText}>Order not found</Text>
              </View>
            ) : (
              <View style={styles.gap16}>
                <OrderStatusCard
                  status={status}
                  vendorName={vendorName}
                  orderType={orderType as any}
                />
                <ETABox
                  etaIso={eta?.estimated_ready_at}
                  isDelayed={eta?.is_delayed}
                  delayMinutes={eta?.delay_minutes}
                />

                {timeline.length > 0 && (
                  <OrderTimeline items={timeline} currentStatus={status} />
                )}

                <View style={styles.card}>
                  <Text style={styles.sectionTitle}>Order Details</Text>
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Vendor</Text>
                    <Text style={styles.detailValue}>{vendorName}</Text>
                  </View>
                  {slotWindow && (
                    <View style={styles.detailRow}>
                      <Text style={styles.detailLabel}>Slot</Text>
                      <Text style={styles.detailValue}>{slotWindow}</Text>
                    </View>
                  )}
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Type</Text>
                    <Text style={styles.detailValue}>
                      {orderType === 'combined' ? 'Food + Stationery' : orderType === 'stationery' ? 'Stationery' : 'Food'}
                    </Text>
                  </View>
                  {totalRupees !== null && (
                    <View style={styles.detailRow}>
                      <Text style={styles.detailLabel}>Total</Text>
                      <Text style={styles.detailValueBold}>
                        ₹{totalRupees.toFixed(2)}
                      </Text>
                    </View>
                  )}
                  {order?.eta_minutes != null && active && (
                    <View style={styles.detailRow}>
                      <Text style={styles.detailLabel}>ETA</Text>
                      <Text style={styles.detailValue}>
                        {order.eta_minutes} min
                      </Text>
                    </View>
                  )}
                </View>

                {items.length > 0 && (
                  <View style={styles.card}>
                    <Text style={styles.sectionTitle}>Food Items</Text>
                    {items.map((item, idx) => (
                      <View
                        key={`${item.name}-${idx}`}
                        style={styles.itemRow}>
                        <Text style={styles.itemName}>{item.name}</Text>
                        <Text style={styles.itemMeta}>x{item.quantity}</Text>
                        <Text style={styles.itemPrice}>
                          ₹
                          {Number(
                            item.line_total ??
                              item.price_at_time * item.quantity,
                          ).toFixed(2)}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}

                {/* Stationery jobs — shown when this is a combined order */}
                {order?.stationery_jobs && order.stationery_jobs.length > 0 && (
                  <View style={styles.card}>
                    <Text style={styles.sectionTitle}>Stationery Jobs</Text>
                    {order.stationery_jobs.map((job, idx) => (
                      <View key={`sj-${job.id}-${idx}`} style={styles.itemRow}>
                        <Text style={styles.itemName}>Service #{job.service_id}</Text>
                        <Text style={styles.itemMeta}>x{job.quantity}</Text>
                        <Text style={styles.itemPrice}>₹{Number(job.amount).toFixed(2)}</Text>
                      </View>
                    ))}
                    <View style={[styles.detailRow, {marginTop: 8}]}>
                      <Text style={styles.detailLabel}>Status</Text>
                      <Text style={styles.detailValue}>{order.stationery_jobs[0].status}</Text>
                    </View>
                  </View>
                )}

                <View style={styles.actions}>
                  {canShowQr && (
                    <GradientButton label="View QR Code" onPress={onQr} />
                  )}
                  {canCancel && (
                    <GradientButton
                      label={cancelling ? 'Cancelling...' : 'Cancel Order'}
                      onPress={onCancel}
                      disabled={cancelling}
                    />
                  )}
                  {canReorder && (
                    <GradientButton
                      label={reordering ? 'Reordering...' : 'Reorder'}
                      onPress={onReorder}
                      disabled={reordering}
                    />
                  )}
                  {canRate && (
                    <GradientButton
                      label="Rate this Order"
                      onPress={onRate}
                    />
                  )}
                </View>
              </View>
            )}
          </>
        )}
      </Screen>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  header: {
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
  },
  sub: {
    fontSize: 14,
    color: '#6B7280',
  },
  liveBadge: {
    backgroundColor: '#D1FAE5',
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  liveBadgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#059669',
  },
  center: {
    paddingVertical: 24,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#9CA3AF',
  },
  gap16: {
    gap: 16,
    paddingBottom: 24,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 16,
    shadowColor: 'rgba(0,0,0,0.08)',
    shadowOpacity: 0.08,
    shadowOffset: {width: 0, height: 3},
    shadowRadius: 8,
    elevation: 4,
    gap: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '800',
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  detailLabel: {
    fontSize: 14,
    color: '#6B7280',
  },
  detailValue: {
    fontSize: 14,
    color: '#111827',
  },
  detailValueBold: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
  },
  itemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 6,
  },
  itemName: {
    fontSize: 14,
    fontWeight: '700',
    flex: 1,
  },
  itemMeta: {
    fontSize: 13,
    color: '#6B7280',
    marginLeft: 10,
  },
  itemPrice: {
    fontSize: 13,
    fontWeight: '700',
    color: '#111827',
    marginLeft: 10,
  },
  actions: {
    gap: 10,
    marginVertical: 10,
  },
});
