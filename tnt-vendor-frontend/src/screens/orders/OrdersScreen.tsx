// ─── Live Order Experience ─────────────────────────────────────────
// Uber-style order management with large cards, timers, badges,
// swipe actions, and real-time status updates

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useAuth } from '../../context/AuthContext';
import { vendorApi, type Order, type OrderMetrics } from '../../services/vendorApi';
import { useWebSocket } from '../../hooks/useWebSocket';
import { WS_BASE_URL } from '../../config/api';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import StatCard from '../../design-system/components/StatCard';
import AnimatedCounter from '../../design-system/components/AnimatedCounter';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';

type TabType = 'live' | 'all' | 'upcoming';
type StatusAction = 'accept' | 'prepare' | 'ready' | 'complete';

const statusConfig: Record<string, { label: string; variant: 'primary' | 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'purple'; icon: string }> = {
  placed: { label: 'Placed', variant: 'primary', icon: '📋' },
  pending: { label: 'Pending', variant: 'primary', icon: '⏳' },
  confirmed: { label: 'Confirmed', variant: 'info', icon: '✅' },
  preparing: { label: 'Preparing', variant: 'warning', icon: '👨‍🍳' },
  ready: { label: 'Ready', variant: 'success', icon: '🍽️' },
  ready_for_pickup: { label: 'Ready', variant: 'success', icon: '🍽️' },
  completed: { label: 'Completed', variant: 'success', icon: '✅' },
  picked: { label: 'Picked Up', variant: 'neutral', icon: '📦' },
  cancelled: { label: 'Cancelled', variant: 'error', icon: '❌' },
};

export default function OrdersScreen() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [metrics, setMetrics] = useState<OrderMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('live');
  const { user, token } = useAuth();
  const navigation = useNavigation();

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
  }, []);

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.3, duration: 1200, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1200, useNativeDriver: true }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, []);

  const loadOrders = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      const res = await vendorApi.getOrders();
      setOrders(res.data.orders);
      setMetrics(res.data.metrics);
    } catch (err) {
      console.error('Failed to load orders:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { loadOrders(); }, [loadOrders]);

  const wsUrl = `${WS_BASE_URL}/ws/vendor/orders`;
  const { isConnected: wsConnected } = useWebSocket(wsUrl, token ?? '');

  const handleStatusUpdate = async (orderId: number, action: StatusAction) => {
    try {
      const actions = { accept: vendorApi.acceptOrder, prepare: vendorApi.prepareOrder, ready: vendorApi.readyOrder, complete: vendorApi.completeOrder };
      await actions[action](orderId);
      loadOrders(true);
    } catch (error) {
      Alert.alert('Error', `Failed to ${action} order`);
    }
  };

  const getNextAction = (status: string): { action: StatusAction | null; label: string; variant: 'primary' | 'success' | 'warning' } => {
    switch (status) {
      case 'placed':
      case 'pending':
        return { action: 'accept', label: 'Accept ✓', variant: 'success' };
      case 'confirmed':
        return { action: 'prepare', label: 'Start Prep', variant: 'warning' };
      case 'preparing':
        return { action: 'ready', label: 'Mark Ready', variant: 'primary' };
      case 'ready':
      case 'ready_for_pickup':
        return { action: 'complete', label: 'Complete', variant: 'success' };
      default:
        return { action: null, label: '', variant: 'primary' };
    }
  };

  const filteredOrders = useMemo(() => {
    if (activeTab === 'live') return orders.filter(o => ['placed', 'pending', 'confirmed', 'preparing', 'ready', 'ready_for_pickup'].includes(o.status));
    if (activeTab === 'upcoming') return orders.filter(o => o.status === 'placed' || o.status === 'pending');
    return orders;
  }, [orders, activeTab]);

  const liveCount = orders.filter(o => ['placed', 'pending', 'confirmed', 'preparing', 'ready', 'ready_for_pickup'].includes(o.status)).length;

  const renderOrderCard = ({ item }: { item: Order }) => {
    const config = statusConfig[item.status] || { label: 'Unknown', variant: 'neutral' as const, icon: '📌' };
    const next = getNextAction(item.status);
    const orderTime = new Date(item.created_at);
    const elapsed = Math.floor((Date.now() - orderTime.getTime()) / 60000);

    return (
      <GlassCard style={styles.orderCard} padding={20} borderRadius={24} intensity="light">
        {/* Top Row — ID + Status + Timer */}
        <View style={styles.orderHeader}>
          <View style={styles.orderIdRow}>
            <View style={styles.orderIdBox}>
              <Text style={styles.orderIdPrefix}>#</Text>
              <Text style={styles.orderIdText}>{item.id}</Text>
            </View>
            {(item as any).is_faculty && (
              <StatusPill label="FACULTY" variant="purple" size="sm" icon="👨‍🏫" />
            )}
            {(item as any).is_group && (
              <StatusPill label="GROUP" variant="warning" size="sm" icon="👥" />
            )}
          </View>
          <StatusPill
            label={config.label}
            variant={config.variant}
            size="sm"
            icon={config.icon}
            animated={item.status === 'preparing'}
          />
        </View>

        {/* Timer Row */}
        <View style={styles.timerRow}>
          <View style={styles.timerItem}>
            <Text style={styles.timerLabel}>Elapsed</Text>
            <Text style={[styles.timerValue, elapsed > 15 ? { color: colors.error } : { color: colors.textPrimary }]}>
              {elapsed}m
            </Text>
          </View>
          {item.eta_minutes != null && (
            <View style={styles.timerItem}>
              <Text style={styles.timerLabel}>ETA</Text>
              <View style={styles.etaBadge}>
                <Text style={styles.etaText}>{item.eta_minutes} min</Text>
              </View>
            </View>
          )}
          {(item as any).is_delayed && (
            <StatusPill label="DELAYED" variant="error" size="sm" icon="⚠️" animated />
          )}
        </View>

        {/* Order Details */}
        <View style={styles.orderDetails}>
          <View style={styles.detailRow}>
            <Text style={styles.detailIcon}>💰</Text>
            <Text style={styles.detailLabel}>Total</Text>
            <Text style={styles.detailValue}>₹{item.total_amount}</Text>
          </View>
          <View style={styles.detailRow}>
            <Text style={styles.detailIcon}>🕐</Text>
            <Text style={styles.detailLabel}>Placed</Text>
            <Text style={styles.detailValue}>
              {orderTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </Text>
          </View>
          {(item as any).customer_notes && (
            <View style={styles.notesRow}>
              <Text style={styles.notesIcon}>📝</Text>
              <Text style={styles.notesText}>{(item as any).customer_notes}</Text>
            </View>
          )}
        </View>

        {/* Action Buttons */}
        {next.action && (
          <View style={styles.actionRow}>
            <TouchableOpacity
              style={[styles.actionButton, next.action === 'accept' ? styles.acceptButton : next.action === 'prepare' ? styles.prepareButton : styles.readyButton]}
              onPress={() => handleStatusUpdate(item.id, next.action!)}
              activeOpacity={0.85}
            >
              <Text style={styles.actionButtonText}>
                {next.action === 'accept' ? '✅ Accept' : next.action === 'prepare' ? '👨‍🍳 Start Prep' : next.action === 'ready' ? '🍽️ Mark Ready' : '✅ Complete'}
              </Text>
            </TouchableOpacity>
            {next.action === 'accept' && (
              <TouchableOpacity
                style={styles.rejectButton}
                onPress={() => Alert.alert('Reject Order', 'Are you sure?')}
              >
                <Text style={styles.rejectButtonText}>✕</Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* Items Preview */}
        {item.items && item.items.length > 0 && (
          <View style={styles.itemsRow}>
            <Text style={styles.itemsLabel}>Items: </Text>
            <Text style={styles.itemsList} numberOfLines={1}>
              {item.items.map(i => `${i.quantity}x ${i.name}`).join(', ')}
            </Text>
          </View>
        )}
      </GlassCard>
    );
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading orders...</Text>
      </View>
    );
  }

  return (
    <Animated.View style={[styles.container, { opacity: fadeAnim }]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <View>
            <Text style={styles.headerTitle}>Orders</Text>
            <Text style={styles.headerSubtitle}>{liveCount} active orders</Text>
          </View>
          <TouchableOpacity style={styles.qrButton} onPress={() => navigation.navigate('QRScanner' as never)}>
            <Text style={styles.qrIcon}>📷</Text>
            <Text style={styles.qrLabel}>Scan</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Live Connection */}
      {wsConnected && (
        <View style={styles.liveBanner}>
          <Animated.View style={[styles.liveDot, { opacity: pulseAnim }]} />
          <View style={[styles.liveDotSolid, { backgroundColor: colors.success }]} />
          <Text style={styles.liveText}>Live — real-time updates active</Text>
        </View>
      )}

      {/* Metrics */}
      {metrics && (
        <View style={styles.metricsRow}>
          <StatCard value={metrics.orders_today} label="Today" icon="📊" color={colors.primary} size="sm" style={{ flex: 1 }} />
          <StatCard value={metrics.pending} label="Pending" icon="⏳" color={colors.statusPlaced} size="sm" style={{ flex: 1 }} />
          <StatCard value={metrics.preparing} label="Prep" icon="👨‍🍳" color={colors.statusPreparing} size="sm" style={{ flex: 1 }} />
          <StatCard value={metrics.ready} label="Ready" icon="🍽️" color={colors.statusReady} size="sm" style={{ flex: 1 }} />
        </View>
      )}

      {/* Tabs */}
      <View style={styles.tabRow}>
        {([
          { key: 'live', label: `Live (${liveCount})` },
          { key: 'all', label: 'All Orders' },
          { key: 'upcoming', label: 'Upcoming' },
        ] as { key: TabType; label: string }[]).map(tab => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, activeTab === tab.key && styles.tabActive]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Text style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Order List */}
      <FlatList
        data={filteredOrders}
        keyExtractor={item => item.id.toString()}
        renderItem={renderOrderCard}
        contentContainerStyle={styles.listContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadOrders(true); }} tintColor={colors.primary} />}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <PremiumEmptyState
            icon="📋"
            title="No orders yet"
            description={activeTab === 'live' ? 'All caught up! New orders will appear here.' : 'No orders found for this filter.'}
          />
        }
      />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },

  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.huge + 20,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
  },
  headerContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  qrButton: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.15)',
    paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12, gap: 6,
  },
  qrIcon: { fontSize: 16 },
  qrLabel: { fontSize: 14, fontWeight: '600', color: colors.textInverse },

  liveBanner: {
    flexDirection: 'row', alignItems: 'center', marginHorizontal: spacing.lg, marginTop: spacing.sm,
    paddingVertical: 8, paddingHorizontal: 14, backgroundColor: colors.successPale,
    borderRadius: 12, borderWidth: 1, borderColor: colors.success + '30',
  },
  liveDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.success, position: 'absolute', left: 14 },
  liveDotSolid: { width: 8, height: 8, borderRadius: 4, marginRight: 8 },
  liveText: { fontSize: 12, fontWeight: '600', color: colors.successDark },

  metricsRow: {
    flexDirection: 'row', paddingHorizontal: spacing.lg, paddingTop: spacing.md, gap: spacing.sm,
  },

  tabRow: {
    flexDirection: 'row', paddingHorizontal: spacing.lg, paddingTop: spacing.md, gap: spacing.sm,
  },
  tab: {
    flex: 1, paddingVertical: 10, borderRadius: 12, backgroundColor: colors.bgCard,
    alignItems: 'center', borderWidth: 1.5, borderColor: colors.border, ...shadows.sm,
  },
  tabActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  tabText: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  tabTextActive: { color: colors.textInverse },

  listContent: { padding: spacing.lg, paddingBottom: spacing.huge },

  orderCard: { marginBottom: spacing.md },
  orderHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12,
  },
  orderIdRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  orderIdBox: { flexDirection: 'row', alignItems: 'baseline', gap: 2 },
  orderIdPrefix: { fontSize: 16, fontWeight: '700', color: colors.textMuted },
  orderIdText: { fontSize: 22, fontWeight: '700', color: colors.textPrimary, letterSpacing: -0.5 },

  timerRow: {
    flexDirection: 'row', alignItems: 'center', gap: 16,
    paddingVertical: 12, borderTopWidth: 1, borderTopColor: colors.borderLight, borderBottomWidth: 1, borderBottomColor: colors.borderLight,
    marginBottom: 12,
  },
  timerItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  timerLabel: { fontSize: 12, color: colors.textMuted, fontWeight: '500' },
  timerValue: { fontSize: 16, fontWeight: '700', fontVariant: ['tabular-nums'] },
  etaBadge: { backgroundColor: colors.primaryPale, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  etaText: { fontSize: 14, fontWeight: '700', color: colors.primary },

  orderDetails: { gap: 6, marginBottom: 12 },
  detailRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  detailIcon: { fontSize: 14 },
  detailLabel: { fontSize: 14, color: colors.textSecondary, fontWeight: '500', flex: 1 },
  detailValue: { fontSize: 14, fontWeight: '700', color: colors.textPrimary },
  notesRow: { flexDirection: 'row', backgroundColor: colors.warningPale, padding: 8, borderRadius: 8, marginTop: 4, gap: 6 },
  notesIcon: { fontSize: 14 },
  notesText: { fontSize: 12, color: colors.warningDark, flex: 1, fontStyle: 'italic' },

  actionRow: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  actionButton: { flex: 1, paddingVertical: 14, borderRadius: 14, alignItems: 'center', ...shadows.button },
  acceptButton: { backgroundColor: colors.success },
  prepareButton: { backgroundColor: colors.warning },
  readyButton: { backgroundColor: colors.primary },
  actionButtonText: { color: colors.textInverse, fontSize: 15, fontWeight: '700' },
  rejectButton: {
    width: 50, height: 50, borderRadius: 14, backgroundColor: colors.errorPale,
    justifyContent: 'center', alignItems: 'center',
  },
  rejectButtonText: { fontSize: 18, color: colors.error, fontWeight: '700' },

  itemsRow: { flexDirection: 'row', paddingTop: 8, borderTopWidth: 1, borderTopColor: colors.borderLight },
  itemsLabel: { fontSize: 12, color: colors.textMuted, fontWeight: '600' },
  itemsList: { fontSize: 12, color: colors.textSecondary, flex: 1 },
});
