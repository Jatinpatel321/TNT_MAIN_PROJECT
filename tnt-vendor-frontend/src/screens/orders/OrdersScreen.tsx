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
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../context/AuthContext';
import { vendorApi, type Order, type OrderMetrics } from '../../services/vendorApi';
import { notificationApi } from '../../services/notificationApi';
import { useVendorWebSocket } from '../../hooks/useVendorWebSocket';
import { colors as staticColors, shadows, spacing } from '../../design-system';
const colors = staticColors;
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import { formatPaise } from '../../utils/format';
import StatCard from '../../design-system/components/StatCard';
import AnimatedCounter from '../../design-system/components/AnimatedCounter';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';
import { useTheme } from '../../context/ThemeContext';
import { useNavigation } from '@react-navigation/native';



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
  const { colors, isDark } = useTheme();
  const styles = getStyles(colors);
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
      console.warn('Failed to load orders:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { loadOrders(); }, [loadOrders]);

  const [wsDisconnected, setWsDisconnected] = useState(false);

  // ── WebSocket — vendor-wide order channel ───────────────────────
  const handleWsEvent = useCallback((evt: { event: string; data: any }) => {
    if (evt.event === 'new_order' && evt.data) {
      setOrders(prev => {
        const exists = prev.some(o => o.id === evt.data.id);
        return exists ? prev : [evt.data, ...prev];
      });
    } else if (evt.event === 'order_updated' && evt.data) {
      setOrders(prev => prev.map(o => o.id === evt.data.id ? { ...o, ...evt.data } : o));
    } else if (evt.event === 'snapshot' && Array.isArray(evt.data)) {
      setOrders(evt.data);
    }
  }, []);

  const { isConnected: wsConnected, reconnectsFailed } = useVendorWebSocket(
    [], // vendor-wide channel
    token ?? null,
    handleWsEvent,
    { useVendorChannel: true, onDisconnected: () => setWsDisconnected(true) },
  );

  // When WS reconnects, clear the banner and refresh
  useEffect(() => {
    if (wsConnected) {
      setWsDisconnected(false);
    }
  }, [wsConnected]);

  // Polling fallback: every 30 s when WS is not connected
  useEffect(() => {
    if (wsConnected) return;
    const id = setInterval(() => loadOrders(true), 30_000);
    return () => clearInterval(id);
  }, [wsConnected, loadOrders]);

  const handleStatusUpdate = async (orderId: number, action: StatusAction) => {
    try {
      const actions = { accept: vendorApi.acceptOrder, prepare: vendorApi.prepareOrder, ready: vendorApi.readyOrder, complete: vendorApi.completeOrder };
      
      const order = orders.find(o => o.id === orderId);
      if (order && order.group_id) {
        const groupMembers = orders.filter(o => o.group_id === order.group_id);
        await Promise.all(groupMembers.map(m => actions[action](m.id)));
      } else {
        await actions[action](orderId);
      }
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

  // Group orders by group_id — group members are collapsed under the first order in their group
  const groupedOrderIds = useMemo(() => {
    const dominated = new Set<number>(); // orders that are grouped under another
    const groupMap: Record<number, Order[]> = {};
    for (const o of filteredOrders) {
      if (o.group_id) {
        if (!groupMap[o.group_id]) groupMap[o.group_id] = [];
        groupMap[o.group_id].push(o);
      }
    }
    // Mark all but the first in each group as dominated
    for (const members of Object.values(groupMap)) {
      members.sort((a, b) => a.id - b.id);
      for (let i = 1; i < members.length; i++) dominated.add(members[i].id);
    }
    return { groupMap, dominated };
  }, [filteredOrders]);

  const displayedOrders = useMemo(
    () => filteredOrders.filter(o => !groupedOrderIds.dominated.has(o.id)),
    [filteredOrders, groupedOrderIds],
  );

  const liveCount = orders.filter(o => ['placed', 'pending', 'confirmed', 'preparing', 'ready', 'ready_for_pickup'].includes(o.status)).length;

  // R11: AI-suggested delay notification trigger
  const [notifyingDelay, setNotifyingDelay] = useState<number | null>(null);
  const handleNotifyDelay = async (order: Order) => {
    const elapsed = Math.floor((Date.now() - new Date(order.created_at).getTime()) / 60000);
    // AI suggestion: suggest delay based on how long the order has been waiting
    const suggestedMinutes = Math.max(5, Math.round(elapsed * 0.4));
    const reason = `Experiencing higher than usual volume. Estimated additional wait: ${suggestedMinutes} minutes.`;

    Alert.alert(
      '⚠️ Notify Customer of Delay',
      `Order #${order.id} has been waiting ${elapsed} minutes.\n\nAI suggests notifying the customer of an additional ${suggestedMinutes} min delay.\n\nReason: ${reason}`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: `Send Delay Alert (+${suggestedMinutes} min)`,
          onPress: async () => {
            setNotifyingDelay(order.id);
            try {
              await notificationApi.notifyDelay(order.id, suggestedMinutes, reason);
              Alert.alert('✅ Sent', `Delay notification sent for order #${order.id}.`);
            } catch (err: any) {
              Alert.alert('Error', err?.message || 'Failed to send delay notification');
            } finally {
              setNotifyingDelay(null);
            }
          },
        },
      ],
    );
  };

  const renderOrderCard = ({ item }: { item: Order }) => {
    const config = statusConfig[item.status] || { label: 'Unknown', variant: 'neutral' as const, icon: '📌' };
    const next = getNextAction(item.status);
    const orderTime = new Date(item.created_at);
    const elapsed = Math.floor((Date.now() - orderTime.getTime()) / 60000);
    const showDelayButton = item.is_delayed || (elapsed > 20 && ['preparing', 'confirmed'].includes(item.status));

    const groupMembers = item.group_id ? groupedOrderIds.groupMap[item.group_id] || [item] : [item];
    const isActualGroup = item.group_id && groupMembers.length > 1;
    const combinedTotal = groupMembers.reduce((sum, o) => sum + o.total_amount, 0);

    const groupedItemsMap: Record<string, number> = {};
    for (const member of groupMembers) {
      if (member.items) {
        for (const i of member.items) {
          groupedItemsMap[i.name] = (groupedItemsMap[i.name] || 0) + i.quantity;
        }
      }
    }
    const combinedItems = Object.entries(groupedItemsMap).map(([name, quantity]) => ({ name, quantity }));

    return (
      <GlassCard style={styles.orderCard} padding={20} borderRadius={24} intensity="light">
        {/* Top Row — ID + Status + Timer */}
        <View style={styles.orderHeader}>
          <View style={styles.orderIdRow}>
            <View style={styles.orderIdBox}>
              <Text style={[styles.orderIdPrefix, { color: colors.textMuted }]}>#</Text>
              <Text style={[styles.orderIdText, { color: colors.textPrimary }]}>{item.id}</Text>
            </View>
            {item.is_faculty && (
              <StatusPill label="FACULTY" variant="purple" size="sm" icon="👨‍🏫" />
            )}
            {item.is_group && (
              <StatusPill label="GROUP" variant="warning" size="sm" icon="👥" />
            )}
            {item.booking_type === 'combined' && (
              <StatusPill label="COMBINED" variant="info" size="sm" icon="🔗" />
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
        <View style={[styles.timerRow, { borderTopColor: colors.borderLight, borderBottomColor: colors.borderLight }]}>
          <View style={styles.timerItem}>
            <Text style={[styles.timerLabel, { color: colors.textMuted }]}>Elapsed</Text>
            <Text style={[styles.timerValue, elapsed > 15 ? { color: colors.error } : { color: colors.textPrimary }]}>
              {elapsed}m
            </Text>
          </View>
          {item.eta_minutes != null && (
            <View style={styles.timerItem}>
              <Text style={[styles.timerLabel, { color: colors.textMuted }]}>ETA</Text>
              <View style={[styles.etaBadge, { backgroundColor: colors.primaryPale }]}>
                <Text style={[styles.etaText, { color: colors.primary }]}>{item.eta_minutes} min</Text>
              </View>
            </View>
          )}
          {item.is_delayed && (
            <StatusPill label="DELAYED" variant="error" size="sm" icon="⚠️" animated />
          )}
        </View>

        {/* Order Details */}
        <View style={styles.orderDetails}>
          <View style={styles.detailRow}>
            <Text style={styles.detailIcon}>💰</Text>
            <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>{isActualGroup ? 'Group Total' : 'Total'}</Text>
            <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{formatPaise(combinedTotal)}</Text>
          </View>
          {/* Group order members summary */}
          {isActualGroup && (
            <View style={[styles.detailRow, { marginTop: 2 }]}>
              <Text style={styles.detailIcon}>👥</Text>
              <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Group</Text>
              <Text style={[styles.detailValue, { color: colors.primary }]}>
                {groupMembers.length} members · {groupMembers.map(m => `#${m.id}`).join(', ')}
              </Text>
            </View>
          )}
          <View style={styles.detailRow}>
            <Text style={styles.detailIcon}>🕐</Text>
            <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Placed</Text>
            <Text style={[styles.detailValue, { color: colors.textPrimary }]}>
              {orderTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </Text>
          </View>
          {item.customer_notes && (
            <View style={[styles.notesRow, { backgroundColor: colors.warningPale }]}>
              <Text style={styles.notesIcon}>📝</Text>
              <Text style={[styles.notesText, { color: colors.warningDark }]}>{item.customer_notes}</Text>
            </View>
          )}
        </View>

        {/* Action Buttons */}
        {next.action && (
          <View style={styles.actionRow}>
            <TouchableOpacity
              style={[
                styles.actionButton,
                next.action === 'accept' ? { backgroundColor: colors.success } : next.action === 'prepare' ? { backgroundColor: colors.warning } : { backgroundColor: colors.primary }
              ]}
              onPress={() => handleStatusUpdate(item.id, next.action!)}
              activeOpacity={0.85}
            >
              <Text style={[styles.actionButtonText, { color: colors.textInverse }]}>
                {next.action === 'accept' ? '✅ Accept' : next.action === 'prepare' ? '👨‍🍳 Start Prep' : next.action === 'ready' ? '🍽️ Mark Ready' : '✅ Complete'}
              </Text>
            </TouchableOpacity>
            {next.action === 'accept' && (
              <TouchableOpacity
                style={[styles.rejectButton, { backgroundColor: colors.errorPale }]}
                onPress={() => Alert.alert('Reject Order', 'Are you sure?')}
              >
                <Text style={[styles.rejectButtonText, { color: colors.error }]}>✕</Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* R11: AI-Suggested Delay Notification Button */}
        {showDelayButton && (
          <TouchableOpacity
            style={[styles.delayButton, { backgroundColor: colors.warningPale, borderColor: colors.warning + '40' }]}
            onPress={() => handleNotifyDelay(item)}
            disabled={notifyingDelay === item.id}
            activeOpacity={0.8}
          >
            {notifyingDelay === item.id ? (
              <ActivityIndicator size="small" color={colors.warning} />
            ) : (
              <>
                <Text style={styles.delayButtonIcon}>⚠️</Text>
                <Text style={[styles.delayButtonText, { color: colors.warningDark }]}>
                  AI: Notify Customer of Delay
                </Text>
              </>
            )}
          </TouchableOpacity>
        )}

        {/* Items Preview */}
        {combinedItems.length > 0 && (
          <View style={[styles.itemsRow, { borderTopColor: colors.borderLight }]}>
            <Text style={[styles.itemsLabel, { color: colors.textMuted }]}>{isActualGroup ? 'Consolidated Items: ' : 'Items: '}</Text>
            <Text style={[styles.itemsList, { color: colors.textSecondary }]} numberOfLines={1}>
              {combinedItems.map(i => `${i.quantity}x ${i.name}`).join(', ')}
            </Text>
          </View>
        )}
      </GlassCard>
    );
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.bg }, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={[styles.loadingText, { color: colors.textMuted }]}>Loading orders...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
      <Animated.View style={{ flex: 1, opacity: fadeAnim }}>
        {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.primary }]}>
        <View style={styles.headerContent}>
          <View>
            <Text style={[styles.headerTitle, { color: colors.textInverse }]}>Orders</Text>
            <Text style={styles.headerSubtitle}>{liveCount} active orders</Text>
          </View>
          <TouchableOpacity style={styles.qrButton} onPress={() => navigation.navigate('QRScanner' as never)}>
            <Text style={styles.qrIcon}>📷</Text>
            <Text style={[styles.qrLabel, { color: colors.textInverse }]}>Scan</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Live Connection */}
      {wsConnected && (
        <View style={[styles.liveBanner, { backgroundColor: colors.successPale, borderColor: colors.success + '30' }]}>
          <Animated.View style={[styles.liveDot, { opacity: pulseAnim }]} />
          <View style={[styles.liveDotSolid, { backgroundColor: colors.success }]} />
          <Text style={[styles.liveText, { color: colors.successDark }]}>Live — real-time updates active</Text>
        </View>
      )}

      {/* WS Disconnected fallback banner */}
      {wsDisconnected && !wsConnected && (
        <TouchableOpacity style={[styles.disconnectedBanner, { backgroundColor: colors.warningPale, borderColor: colors.warning + '40' }]} onPress={() => loadOrders(true)} activeOpacity={0.8}>
          <Text style={[styles.disconnectedText, { color: colors.warningDark }]}>⚠ Live updates paused — tap to refresh</Text>
        </TouchableOpacity>
      )}

      {/* Metrics */}
      {metrics && (
        <View style={styles.metricsRow}>
          <StatCard value={metrics.orders_today} label="Today" icon="📊" color={colors.primary} size="sm" style={{ flexBasis: '45%', flexGrow: 1 }} />
          <StatCard value={metrics.pending} label="Pending" icon="⏳" color={colors.statusPlaced} size="sm" style={{ flexBasis: '45%', flexGrow: 1 }} />
          <StatCard value={metrics.preparing} label="Prep" icon="👨‍🍳" color={colors.statusPreparing} size="sm" style={{ flexBasis: '45%', flexGrow: 1 }} />
          <StatCard value={metrics.ready} label="Ready" icon="🍽️" color={colors.statusReady} size="sm" style={{ flexBasis: '45%', flexGrow: 1 }} />
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
            style={[
              styles.tab,
              { backgroundColor: colors.bgCard, borderColor: colors.border },
              activeTab === tab.key && [styles.tabActive, { backgroundColor: colors.primary, borderColor: colors.primary }]
            ]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Text style={[
              styles.tabText,
              { color: colors.textSecondary },
              activeTab === tab.key && [styles.tabTextActive, { color: colors.textInverse }]
            ]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Order List */}
      <FlatList
        data={displayedOrders}
        keyExtractor={item => item.id.toString()}
        renderItem={renderOrderCard}
        contentContainerStyle={[styles.listContent, { paddingBottom: 100 }]}
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
    </SafeAreaView>
  );
}

const getStyles = (colors: any) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },

  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.lg,
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

  disconnectedBanner: {
    marginHorizontal: spacing.lg,
    marginTop: spacing.sm,
    paddingVertical: 10,
    paddingHorizontal: 14,
    backgroundColor: colors.warningPale,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.warning + '40',
    alignItems: 'center',
  },
  disconnectedText: { fontSize: 12, fontWeight: '700', color: colors.warningDark },

  metricsRow: {
    flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: spacing.lg, paddingTop: spacing.md, gap: spacing.sm,
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

  // R11: Delay notification button
  delayButton: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    paddingVertical: 12, borderRadius: 14, marginBottom: 12,
    borderWidth: 1.5,
  },
  delayButtonIcon: { fontSize: 16 },
  delayButtonText: { fontSize: 13, fontWeight: '700' },
});
