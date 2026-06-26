import React, {useState, useEffect, useCallback, useMemo, useRef} from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {useAuth} from '../../context/AuthContext';
import {vendorApi, type Order, type OrderMetrics} from '../../services/vendorApi';
import {useWebSocket} from '../../hooks/useWebSocket';

type TabType = 'all' | 'current' | 'upcoming';
type StatusAction = 'accept' | 'prepare' | 'ready' | 'complete';

export default function OrdersScreen() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [metrics, setMetrics] = useState<OrderMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('all');
  const {user, token} = useAuth();
  const navigation = useNavigation();

  // ── Collect order IDs for WebSocket subscription ─────────────────────
  const activeOrderIds = useMemo(() => {
    return orders
      .filter(o => !['picked', 'completed', 'cancelled'].includes(o.status))
      .map(o => o.id);
  }, [orders]);

  // ── WebSocket event handler ──────────────────────────────────────────
  const handleWSEvent = useCallback((event: {event: string; data: any}) => {
    const {event: eventType, data} = event;

    switch (eventType) {
      case 'snapshot':
        // Initial full list of active orders
        if (Array.isArray(data)) {
          setOrders(prev => {
            const incomingMap = new Map(data.map((o: any) => [o.id, o]));
            // Merge: keep existing orders, update with snapshot, keep non-active ones not in snapshot
            const updated = prev.map(o =>
              incomingMap.has(o.id) ? {...o, ...incomingMap.get(o.id)} : o,
            );
            // Add any snapshot orders not already in the list
            const existingIds = new Set(prev.map(o => o.id));
            for (const o of data) {
              if (!existingIds.has(o.id)) {
                updated.push({...o, qr_code: undefined});
              }
            }
            return updated;
          });
        }
        break;

      case 'status_change':
        setOrders(prev =>
          prev.map(o =>
            o.id === data.order_id
              ? {...o, status: data.new_status, eta_minutes: data.eta_minutes ?? o.eta_minutes}
              : o,
          ),
        );
        break;

      case 'new_order':
        // A brand-new order arrived — prepend to list
        setOrders(prev => {
          if (prev.some(o => o.id === data.id)) return prev;
          return [{...data, qr_code: undefined}, ...prev];
        });
        break;

      case 'eta_update':
        setOrders(prev =>
          prev.map(o =>
            o.id === data.order_id
              ? {...o, eta_minutes: data.eta_minutes ?? o.eta_minutes}
              : o,
          ),
        );
        break;

      case 'pickup_confirmed':
        setOrders(prev =>
          prev.map(o =>
            o.id === data.order_id ? {...o, status: 'picked'} : o,
          ),
        );
        break;
    }
  }, []);

  // ── Load initial data ────────────────────────────────────────────────
  const loadOrders = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      const response = await vendorApi.getOrders();
      setOrders(response.data.orders);
      setMetrics(response.data.metrics);
    } catch (error) {
      console.error('Failed to load orders:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  // ── WS base URL (derive from API_BASE_URL) ───────────────────────────
  const wsVendorUrl = 'ws://localhost:8000/ws/vendor/orders';

  // ── Connect vendor dashboard WebSocket ───────────────────────────────
  const {isConnected: wsConnected, lastMessage} = useWebSocket(
    wsVendorUrl,
    token ?? '',
  );

  // ── Reload on WS event ────────────────────────────────────────────────
  useEffect(() => {
    if (lastMessage?.data?.order_id || lastMessage?.event) {
      loadOrders(true);
    }
  }, [lastMessage, loadOrders]);

  // ── 15-second polling fallback ───────────────────────────────────────
  useEffect(() => {
    if (wsConnected) {
      // WebSocket active — stop polling
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    } else {
      // No WS — start polling
      pollTimerRef.current = setInterval(() => {
        loadOrders(true);
      }, 15000);
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [wsConnected, loadOrders]);

  const onRefresh = () => {
    setRefreshing(true);
    loadOrders(true);
  };

  const handleStatusUpdate = async (orderId: number, action: StatusAction) => {
    try {
      let apiCall;
      switch (action) {
        case 'accept':
          apiCall = vendorApi.acceptOrder(orderId);
          break;
        case 'prepare':
          apiCall = vendorApi.prepareOrder(orderId);
          break;
        case 'ready':
          apiCall = vendorApi.readyOrder(orderId);
          break;
        case 'complete':
          apiCall = vendorApi.completeOrder(orderId);
          break;
      }
      await apiCall;
      // The WebSocket will update the list in real-time; refresh for full consistency
      loadOrders(true);
    } catch (error) {
      Alert.alert('Error', `Failed to ${action} order`);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready':
      case 'ready_for_pickup':
        return '#10B981';
      case 'preparing':
        return '#F59E0B';
      case 'confirmed':
        return '#3B82F6';
      case 'placed':
      case 'pending':
        return '#8B5CF6';
      case 'picked':
      case 'completed':
        return '#6B7280';
      case 'cancelled':
        return '#EF4444';
      default:
        return '#6B7280';
    }
  };

  const getNextAction = (
    status: string,
  ): {action: StatusAction | null; label: string} => {
    switch (status) {
      case 'placed':
      case 'pending':
        return {action: 'accept', label: 'Accept'};
      case 'confirmed':
        return {action: 'prepare', label: 'Start Preparing'};
      case 'preparing':
        return {action: 'ready', label: 'Mark Ready'};
      case 'ready':
      case 'ready_for_pickup':
        return {action: 'complete', label: 'Complete'};
      default:
        return {action: null, label: ''};
    }
  };

  const filteredOrders = useMemo(() => {
    if (activeTab === 'current')
      return orders.filter(
        o => o.status === 'preparing' || o.status === 'confirmed',
      );
    if (activeTab === 'upcoming')
      return orders.filter(
        o => o.status === 'placed' || o.status === 'pending',
      );
    return orders;
  }, [orders, activeTab]);

  const renderOrderCard = ({item}: {item: Order}) => {
    const nextAction = getNextAction(item.status);

    return (
      <View style={styles.orderCard}>
        <View style={styles.orderHeader}>
          <Text style={styles.orderId}>Order #{item.id}</Text>
          <View
            style={[
              styles.statusBadge,
              {backgroundColor: getStatusColor(item.status)},
            ]}>
            <Text style={styles.statusText}>
              {item.status.toUpperCase()}
            </Text>
          </View>
        </View>

        <View style={styles.orderDetails}>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Amount:</Text>
            <Text style={styles.detailValue}>₹{item.total_amount}</Text>
          </View>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Time:</Text>
            <Text style={styles.detailValue}>
              {new Date(item.created_at).toLocaleTimeString()}
            </Text>
          </View>
          {item.eta_minutes != null && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>ETA:</Text>
              <Text style={styles.detailValue}>{item.eta_minutes} min</Text>
            </View>
          )}
          {item.qr_code && (
            <View style={styles.detailRow}>
              <Text
                style={[styles.detailLabel, {color: '#10B981', fontWeight: '600'}]}>
                ✅ QR Code Available
              </Text>
            </View>
          )}
        </View>

        {nextAction.action && (
          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => handleStatusUpdate(item.id, nextAction.action!)}>
            <Text style={styles.actionButtonText}>
              {nextAction.label}
            </Text>
          </TouchableOpacity>
        )}
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#10B981" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Connection Indicator */}
      {wsConnected && (
        <View style={styles.liveBanner}>
          <View style={styles.liveDot} />
          <Text style={styles.liveText}>Live — real-time updates active</Text>
        </View>
      )}

      {/* Metrics Cards */}
      {metrics && (
        <View style={styles.metricsContainer}>
          <View style={styles.metricCard}>
            <Text style={styles.metricValue}>{metrics.orders_today}</Text>
            <Text style={styles.metricLabel}>Today</Text>
          </View>
          <View style={styles.metricCard}>
            <Text style={[styles.metricValue, {color: '#8B5CF6'}]}>
              {metrics.pending}
            </Text>
            <Text style={styles.metricLabel}>Pending</Text>
          </View>
          <View style={styles.metricCard}>
            <Text style={[styles.metricValue, {color: '#F59E0B'}]}>
              {metrics.preparing}
            </Text>
            <Text style={styles.metricLabel}>Preparing</Text>
          </View>
          <View style={styles.metricCard}>
            <Text style={[styles.metricValue, {color: '#10B981'}]}>
              {metrics.ready}
            </Text>
            <Text style={styles.metricLabel}>Ready</Text>
          </View>
        </View>
      )}

      {/* Scan QR Button */}
      <TouchableOpacity
        style={styles.scanQRButton}
        onPress={() => navigation.navigate('QRScanner' as never)}
      >
        <Text style={styles.scanQRButtonText}>📷 Scan QR Code</Text>
      </TouchableOpacity>

      {/* Tab Selector */}
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'all' && styles.activeTab]}
          onPress={() => setActiveTab('all')}>
          <Text
            style={[
              styles.tabText,
              activeTab === 'all' && styles.activeTabText,
            ]}>
            All
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'current' && styles.activeTab]}
          onPress={() => setActiveTab('current')}>
          <Text
            style={[
              styles.tabText,
              activeTab === 'current' && styles.activeTabText,
            ]}>
            Current
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'upcoming' && styles.activeTab]}
          onPress={() => setActiveTab('upcoming')}>
          <Text
            style={[
              styles.tabText,
              activeTab === 'upcoming' && styles.activeTabText,
            ]}>
            Upcoming
          </Text>
        </TouchableOpacity>
      </View>

      {/* Orders List */}
      <FlatList
        data={filteredOrders}
        keyExtractor={item => item.id.toString()}
        renderItem={renderOrderCard}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyIcon}>
              {activeTab === 'all' ? '📋' : '✅'}
            </Text>
            <Text style={styles.emptyTitle}>No orders</Text>
            <Text style={styles.emptySub}>
              {activeTab === 'all'
                ? 'No orders yet for this vendor'
                : activeTab === 'current'
                  ? 'No orders currently being prepared'
                  : 'No upcoming orders'}
            </Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  liveBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#D1FAE5',
    paddingVertical: 6,
    paddingHorizontal: 16,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#059669',
    marginRight: 8,
  },
  liveText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#065F46',
  },
  metricsContainer: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  metricCard: {
    flex: 1,
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  metricValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#10B981',
    marginBottom: 4,
  },
  metricLabel: {
    fontSize: 12,
    color: '#6B7280',
  },
  scanQRButton: {
    marginHorizontal: 16,
    marginBottom: 12,
    paddingVertical: 14,
    borderRadius: 10,
    backgroundColor: '#059669',
    alignItems: 'center',
  },
  scanQRButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginBottom: 16,
    gap: 8,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: 'white',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  activeTab: {
    backgroundColor: '#10B981',
    borderColor: '#10B981',
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
  },
  activeTabText: {
    color: 'white',
  },
  listContainer: {
    padding: 16,
    paddingBottom: 40,
  },
  orderCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  orderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  orderId: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  orderDetails: {
    marginBottom: 12,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  detailLabel: {
    fontSize: 14,
    color: '#6B7280',
  },
  detailValue: {
    fontSize: 14,
    color: '#111827',
    fontWeight: '500',
  },
  actionButton: {
    backgroundColor: '#10B981',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
  },
  actionButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  emptyContainer: {
    alignItems: 'center',
    paddingTop: 40,
    gap: 8,
  },
  emptyIcon: {
    fontSize: 48,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
  },
  emptySub: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
  },
});
