import React, {useState, useEffect, useCallback, useMemo, useRef} from 'react';
import {
  ActivityIndicator,
  Alert,
  Animated,
  FlatList,
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
import {
  Colors,
  Typography,
  Spacing,
  Shadows,
  BorderRadius,
  getStatusColor,
  getStatusLabel,
  getStatusIcon,
} from '../../theme';
import Card from '../../components/Card';
import Badge from '../../components/Badge';
import MetricCard from '../../components/MetricCard';
import Button from '../../components/Button';

type TabType = 'all' | 'current' | 'upcoming';
type StatusAction = 'accept' | 'prepare' | 'ready' | 'complete';

// Map order status to Badge variant
const statusToBadgeVariant: Record<string, 'primary' | 'success' | 'warning' | 'error' | 'info' | 'neutral'> = {
  placed: 'primary',
  pending: 'primary',
  confirmed: 'info',
  preparing: 'warning',
  ready: 'success',
  ready_for_pickup: 'success',
  completed: 'success',
  picked: 'neutral',
  cancelled: 'error',
};

export default function OrdersScreen() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [metrics, setMetrics] = useState<OrderMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('all');
  const {user, token} = useAuth();
  const navigation = useNavigation();

  // ── Animation values ─────────────────────────────────────────────────
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // ── Pulse animation for live dot ─────────────────────────────────────
  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 0.3,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, [pulseAnim]);

  // ── Entrance animation ────────────────────────────────────────────────
  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 500,
      useNativeDriver: true,
    }).start();
  }, [fadeAnim]);

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
    const statusColor = getStatusColor(item.status);
    const statusLabel = getStatusLabel(item.status);
    const statusIcon = getStatusIcon(item.status);
    const badgeVariant = statusToBadgeVariant[item.status] || 'neutral';

    return (
      <Card variant="elevated" style={styles.orderCard} padding={Spacing.lg}>
        {/* Header Row: Order ID + Status Badge + Icon */}
        <View style={styles.orderHeader}>
          <View style={styles.orderIdRow}>
            <Text style={styles.orderIdPrefix}>#</Text>
            <Text style={styles.orderId}>{item.id}</Text>
          </View>
          <Badge
            label={statusLabel}
            variant={badgeVariant}
            icon={statusIcon}
            size="md"
          />
        </View>

        {/* Gradient-like separator line */}
        <View style={styles.separator} />

        {/* Order Details */}
        <View style={styles.orderDetails}>
          <View style={styles.detailRow}>
            <View style={styles.detailLeft}>
              <Text style={styles.detailIcon}>💰</Text>
              <Text style={styles.detailLabel}>Amount</Text>
            </View>
            <Text style={styles.detailValue}>₹{item.total_amount}</Text>
          </View>
          <View style={styles.detailRow}>
            <View style={styles.detailLeft}>
              <Text style={styles.detailIcon}>🕐</Text>
              <Text style={styles.detailLabel}>Time</Text>
            </View>
            <Text style={styles.detailValue}>
              {new Date(item.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          </View>
          {item.eta_minutes != null && (
            <View style={styles.detailRow}>
              <View style={styles.detailLeft}>
                <Text style={styles.detailIcon}>⏱️</Text>
                <Text style={styles.detailLabel}>ETA</Text>
              </View>
              <View style={styles.etaBadge}>
                <Text style={[styles.detailValue, {color: Colors.primary}]}>
                  {item.eta_minutes} min
                </Text>
              </View>
            </View>
          )}
          {item.qr_code && (
            <View style={styles.detailRow}>
              <View style={styles.detailLeft}>
                <Text style={styles.detailIcon}>✅</Text>
                <Text style={styles.detailLabel}>QR Code</Text>
              </View>
              <Text style={[styles.detailValue, {color: Colors.success, fontWeight: Typography.semibold}]}>
                Available
              </Text>
            </View>
          )}
        </View>

        {/* Action Button */}
        {nextAction.action && (
          <View style={styles.actionSection}>
            <Button
              title={nextAction.label}
              onPress={() => handleStatusUpdate(item.id, nextAction.action!)}
              variant={nextAction.action === 'accept' ? 'success' : 'primary'}
              size="md"
              icon={
                nextAction.action === 'accept'
                  ? '✅'
                  : nextAction.action === 'prepare'
                    ? '👨‍🍳'
                    : nextAction.action === 'ready'
                      ? '🍽️'
                      : '✅'
              }
              fullWidth
            />
          </View>
        )}
      </Card>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <View style={styles.loadingContent}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading orders...</Text>
        </View>
      </View>
    );
  }

  return (
    <Animated.View style={[styles.container, {opacity: fadeAnim}]}>
      {/* ── Header with gradient effect ── */}
      <View style={styles.header}>
        <View style={styles.headerBg}>
          <View style={styles.headerOverlay} />
        </View>
        <View style={styles.headerContent}>
          <Text style={styles.headerTitle}>Orders</Text>
          <Text style={styles.headerSubtitle}>
            {filteredOrders.length} order{filteredOrders.length !== 1 ? 's' : ''}
          </Text>
        </View>
      </View>

      {/* ── Live Connection Banner ── */}
      {wsConnected && (
        <View style={styles.liveBanner}>
          <View style={styles.liveBannerInner}>
            <Animated.View
              style={[
                styles.liveDot,
                {
                  opacity: pulseAnim,
                  backgroundColor: Colors.success,
                },
              ]}
            />
            <View style={[styles.liveDotSolid, {backgroundColor: Colors.success}]} />
            <Text style={styles.liveText}>Live — real-time updates active</Text>
          </View>
        </View>
      )}

      {/* ── Metrics Cards ── */}
      {metrics && (
        <View style={styles.metricsContainer}>
          <MetricCard
            value={metrics.orders_today}
            label="Today"
            icon="📊"
            color={Colors.primary}
            size="sm"
            style={styles.metricCardItem}
          />
          <MetricCard
            value={metrics.pending}
            label="Pending"
            icon="⏳"
            color={getStatusColor('pending')}
            size="sm"
            style={styles.metricCardItem}
          />
          <MetricCard
            value={metrics.preparing}
            label="Preparing"
            icon="👨‍🍳"
            color={getStatusColor('preparing')}
            size="sm"
            style={styles.metricCardItem}
          />
          <MetricCard
            value={metrics.ready}
            label="Ready"
            icon="🍽️"
            color={getStatusColor('ready')}
            size="sm"
            style={styles.metricCardItem}
          />
        </View>
      )}

      {/* ── Scan QR Button ── */}
      <View style={styles.scanQRContainer}>
        <Button
          title="Scan QR Code"
          onPress={() => navigation.navigate('QRScanner' as never)}
          variant="outline"
          size="md"
          icon="📷"
          fullWidth
        />
      </View>

      {/* ── Tab Selector ── */}
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'all' && styles.activeTab]}
          onPress={() => setActiveTab('all')}>
          <View style={styles.tabInner}>
            {activeTab === 'all' && <View style={styles.tabActiveIndicator} />}
            <Text
              style={[
                styles.tabText,
                activeTab === 'all' && styles.activeTabText,
              ]}>
              All
            </Text>
          </View>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'current' && styles.activeTab]}
          onPress={() => setActiveTab('current')}>
          <View style={styles.tabInner}>
            {activeTab === 'current' && <View style={styles.tabActiveIndicator} />}
            <Text
              style={[
                styles.tabText,
                activeTab === 'current' && styles.activeTabText,
              ]}>
              Current
            </Text>
          </View>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'upcoming' && styles.activeTab]}
          onPress={() => setActiveTab('upcoming')}>
          <View style={styles.tabInner}>
            {activeTab === 'upcoming' && <View style={styles.tabActiveIndicator} />}
            <Text
              style={[
                styles.tabText,
                activeTab === 'upcoming' && styles.activeTabText,
              ]}>
              Upcoming
            </Text>
          </View>
        </TouchableOpacity>
      </View>

      {/* ── Orders List ── */}
      <FlatList
        data={filteredOrders}
        keyExtractor={item => item.id.toString()}
        renderItem={renderOrderCard}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={Colors.primary}
            colors={[Colors.primary]}
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <View style={styles.emptyIconCircle}>
              <Text style={styles.emptyIcon}>
                {activeTab === 'all' ? '📋' : '✅'}
              </Text>
            </View>
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
        showsVerticalScrollIndicator={false}
      />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.bg,
  },
  loadingContent: {
    alignItems: 'center',
    gap: Spacing.md,
  },
  loadingText: {
    fontSize: Typography.bodySmall,
    color: Colors.textMuted,
    fontWeight: Typography.medium,
  },

  // ── Header ──
  header: {
    backgroundColor: Colors.primary,
    paddingTop: Spacing.xxxl,
    paddingBottom: Spacing.xxl,
    paddingHorizontal: Spacing.xl,
    borderBottomLeftRadius: BorderRadius.xl,
    borderBottomRightRadius: BorderRadius.xl,
    ...Shadows.header,
  },
  headerBg: {
    ...StyleSheet.absoluteFillObject,
    borderBottomLeftRadius: BorderRadius.xl,
    borderBottomRightRadius: BorderRadius.xl,
    overflow: 'hidden',
  },
  headerOverlay: {
    flex: 1,
    backgroundColor: Colors.primaryDark,
    opacity: 0.15,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  },
  headerTitle: {
    fontSize: Typography.h2,
    fontWeight: Typography.bold,
    color: Colors.textInverse,
  },
  headerSubtitle: {
    fontSize: Typography.bodySmall,
    color: Colors.textInverse,
    opacity: 0.85,
    fontWeight: Typography.medium,
  },

  // ── Live Banner ──
  liveBanner: {
    marginHorizontal: Spacing.lg,
    marginTop: Spacing.md,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.primaryPale,
    borderWidth: 1.5,
    borderColor: Colors.primaryLight,
    overflow: 'hidden',
    ...Shadows.card,
  },
  liveBannerInner: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.sm + 2,
    paddingHorizontal: Spacing.lg,
  },
  liveDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: Spacing.sm,
    position: 'absolute',
    left: Spacing.lg,
  },
  liveDotSolid: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: Spacing.sm,
  },
  liveText: {
    fontSize: Typography.caption,
    fontWeight: Typography.semibold,
    color: Colors.primaryDark,
    letterSpacing: 0.3,
  },

  // ── Metrics ──
  metricsContainer: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
    gap: Spacing.sm,
    flexWrap: 'wrap',
  },
  metricCardItem: {
    flex: 1,
    minWidth: '22%',
  },

  // ── Scan QR Button ──
  scanQRContainer: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
  },

  // ── Tab Selector ──
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.sm,
    gap: Spacing.sm,
  },
  tab: {
    flex: 1,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.bgCard,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: Colors.border,
    ...Shadows.card,
  },
  activeTab: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  tabInner: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.xs,
  },
  tabActiveIndicator: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.textInverse,
  },
  tabText: {
    fontSize: Typography.bodySmall,
    fontWeight: Typography.semibold,
    color: Colors.textSecondary,
  },
  activeTabText: {
    color: Colors.textInverse,
  },

  // ── Orders List ──
  listContainer: {
    padding: Spacing.lg,
    paddingBottom: Spacing.huge,
  },

  // ── Order Card ──
  orderCard: {
    marginBottom: Spacing.md,
  },
  orderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  orderIdRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 2,
  },
  orderIdPrefix: {
    fontSize: Typography.h4,
    fontWeight: Typography.bold,
    color: Colors.textMuted,
  },
  orderId: {
    fontSize: Typography.h3,
    fontWeight: Typography.bold,
    color: Colors.textPrimary,
  },
  separator: {
    height: 2,
    backgroundColor: Colors.bgTertiary,
    borderRadius: 1,
    marginBottom: Spacing.md,
  },
  orderDetails: {
    gap: Spacing.sm,
    marginBottom: Spacing.md,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  detailLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  detailIcon: {
    fontSize: Typography.bodySmall,
  },
  detailLabel: {
    fontSize: Typography.bodySmall,
    color: Colors.textSecondary,
    fontWeight: Typography.medium,
  },
  detailValue: {
    fontSize: Typography.bodySmall,
    color: Colors.textPrimary,
    fontWeight: Typography.semibold,
  },
  etaBadge: {
    backgroundColor: Colors.primaryPale,
    paddingHorizontal: Spacing.sm + 2,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.sm,
  },
  actionSection: {
    marginTop: Spacing.xs,
  },

  // ── Empty State ──
  emptyContainer: {
    alignItems: 'center',
    paddingTop: Spacing.huge,
    paddingHorizontal: Spacing.xxl,
    gap: Spacing.md,
  },
  emptyIconCircle: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: Colors.bgTertiary,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  emptyIcon: {
    fontSize: 32,
  },
  emptyTitle: {
    fontSize: Typography.h4,
    fontWeight: Typography.bold,
    color: Colors.textPrimary,
  },
  emptySub: {
    fontSize: Typography.bodySmall,
    color: Colors.textMuted,
    textAlign: 'center',
    lineHeight: 20,
  },
});