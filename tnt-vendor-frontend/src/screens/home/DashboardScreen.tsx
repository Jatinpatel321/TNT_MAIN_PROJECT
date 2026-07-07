// ─── Executive Dashboard ────────────────────────────────────────────
// Premium command center with AI-powered insights, live metrics,
// revenue tracking, demand forecasting, and business health

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Animated,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../context/AuthContext';
import { vendorApi, type DashboardMetrics } from '../../services/vendorApi';
import { useTheme } from '../../context/ThemeContext';
import { colors as staticColors, shadows, spacing } from '../../design-system';
const colors = staticColors;


import StatCard from '../../design-system/components/StatCard';
import GlassCard from '../../design-system/components/GlassCard';
import ProgressRing from '../../design-system/components/ProgressRing';
import StatusPill from '../../design-system/components/StatusPill';
import AICard from '../../design-system/components/AICard';
import AnimatedCounter from '../../design-system/components/AnimatedCounter';
import { formatPaise } from '../../utils/format';


const { width } = Dimensions.get('window');
const CARD_WIDTH = (width - 48) / 2;

type StatusVariant = 'primary' | 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'purple';

const ORDER_STATUS: Record<string, { label: string; variant: StatusVariant; color: string }> = {
  placed: { label: 'Placed', variant: 'primary', color: staticColors.statusPlaced },
  pending: { label: 'Pending', variant: 'primary', color: staticColors.statusPlaced },
  confirmed: { label: 'Confirmed', variant: 'info', color: staticColors.statusConfirmed },
  preparing: { label: 'Preparing', variant: 'warning', color: staticColors.statusPreparing },
  ready: { label: 'Ready', variant: 'success', color: staticColors.statusReady },
  ready_for_pickup: { label: 'Ready', variant: 'success', color: staticColors.statusReady },
  completed: { label: 'Completed', variant: 'success', color: staticColors.statusCompleted },
  picked: { label: 'Picked', variant: 'neutral', color: staticColors.statusPicked },
  cancelled: { label: 'Cancelled', variant: 'error', color: staticColors.statusCancelled },
};

export default function DashboardScreen({ navigation }: any) {
  const { user } = useAuth();
  const { colors, isDark } = useTheme();
  const styles = getStyles(colors);
  const [data, setData] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 500,
      useNativeDriver: true,
    }).start();
  }, []);

  const fetchData = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      setError(null);
      const res = await vendorApi.getDashboardMetrics();
      setData(res.data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData(true);
  }, [fetchData]);

  const navigateTo = (screen: string) => navigation.navigate(screen);

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.bg }, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={[styles.loadingText, { color: colors.textMuted }]}>Loading your command center...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
      <ScrollView
        style={{ flex: 1 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
        showsVerticalScrollIndicator={false}
      >
      {/* ── Premium Header ── */}
      <View style={[styles.header, { backgroundColor: colors.primary }]}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <View style={styles.headerContent}>
          <View style={styles.headerLeft}>
            <Text style={styles.greeting}>
              Good {new Date().getHours() < 12 ? 'Morning' : new Date().getHours() < 17 ? 'Afternoon' : 'Evening'},
            </Text>
            <Text style={[styles.vendorName, { color: colors.textInverse }]}>{user?.vendor_name || 'Vendor'}</Text>
            <View style={styles.headerStatusRow}>
              <StatusPill label="OPEN" variant="success" size="sm" animated />
              <StatusPill
                label={`${data?.avg_rating?.toFixed(1) || '0.0'} ★`}
                variant="warning"
                size="sm"
              />
            </View>
          </View>
          <View style={styles.headerRight}>
            <TouchableOpacity style={styles.notifBell} onPress={() => navigateTo('Notifications')}>
              <Text style={styles.bellIcon}>🔔</Text>
            </TouchableOpacity>
            <Text style={styles.headerDate}>
              {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </Text>
          </View>
        </View>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        {/* ── Business Health ── */}
        <View style={styles.healthSection}>
          <GlassCard intensity="light" padding={16} borderRadius={20}>
            <View style={styles.healthRow}>
              <ProgressRing
                progress={Math.min(data?.completed_orders ? (data.completed_orders / Math.max(data.orders_today, 1)) * 100 : 0, 100)}
                size={70}
                strokeWidth={6}
                color={colors.primary}
                showPercentage
              />
              <View style={styles.healthInfo}>
                <Text style={[styles.healthTitle, { color: colors.textPrimary }]}>Today's Progress</Text>
                <Text style={[styles.healthSubtitle, { color: colors.textMuted }]}>
                  {data?.completed_orders ?? 0} of {data?.orders_today ?? 0} orders completed
                </Text>
                <View style={styles.healthStats}>
                  <View style={styles.healthStat}>
                    <Text style={[styles.healthStatValue, { color: colors.textPrimary }]}>{data?.avg_rating?.toFixed(1) || '0.0'}</Text>
                    <Text style={[styles.healthStatLabel, { color: colors.textMuted }]}>Rating</Text>
                  </View>
                  <View style={styles.healthStat}>
                    <Text style={[styles.healthStatValue, { color: colors.textPrimary }]}>{data?.active_slots ?? 0}</Text>
                    <Text style={[styles.healthStatLabel, { color: colors.textMuted }]}>Slots</Text>
                  </View>
                  <View style={styles.healthStat}>
                    <Text style={[styles.healthStatValue, { color: colors.textPrimary }]}>{data?.pending_orders ?? 0}</Text>
                    <Text style={[styles.healthStatLabel, { color: colors.textMuted }]}>Pending</Text>
                  </View>
                </View>
              </View>
            </View>
          </GlassCard>
        </View>

        {/* ── Key Metrics ── */}
        <View style={styles.statsGrid}>
          <StatCard
            value={data?.revenue_today ?? 0}
            label="Today's Revenue"
            prefix="₹"
            color={colors.primary}
            icon="💰"
            format="currency"
            style={{ flexBasis: '45%', flexGrow: 1 }}
          />
          <StatCard
            value={data?.orders_today ?? 0}
            label="Orders Today"
            color={colors.secondary}
            icon="📦"
            style={{ flexBasis: '45%', flexGrow: 1 }}
          />
        </View>

        {/* ── Order Status Summary ── */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
            <Text style={[styles.sectionAccent, { color: colors.primary }]}>│</Text> Order Status
          </Text>
          <View style={styles.orderStatusGrid}>
            <TouchableOpacity style={[styles.orderStatusCard, { backgroundColor: colors.bgCard }]} onPress={() => navigateTo('Orders')}>
              <View style={[styles.orderStatusIcon, { backgroundColor: colors.statusPlaced + '15' }]}>
                <Text style={styles.orderStatusEmoji}>⏳</Text>
              </View>
              <AnimatedCounter value={data?.pending_orders ?? 0} fontSize={20} color={colors.statusPlaced} />
              <Text style={[styles.orderStatusLabel, { color: colors.textMuted }]}>Pending</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.orderStatusCard, { backgroundColor: colors.bgCard }]} onPress={() => navigateTo('Orders')}>
              <View style={[styles.orderStatusIcon, { backgroundColor: colors.statusConfirmed + '15' }]}>
                <Text style={styles.orderStatusEmoji}>✅</Text>
              </View>
              <AnimatedCounter value={data?.completed_orders ?? 0} fontSize={20} color={colors.statusConfirmed} />
              <Text style={[styles.orderStatusLabel, { color: colors.textMuted }]}>Completed</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* ── Revenue Trend ── */}
        {data?.revenue_trend && data.revenue_trend.length > 0 && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
              <Text style={[styles.sectionAccent, { color: colors.primary }]}>│</Text> Revenue Trend
            </Text>
            <GlassCard padding={20} borderRadius={24}>
              <View style={styles.revenueChart}>
                {data.revenue_trend.map((day, index) => {
                  const maxRev = Math.max(...data!.revenue_trend.map(d => d.revenue), 1);
                  const heightPct = (day.revenue / maxRev) * 100;
                  const isToday = index === data!.revenue_trend.length - 1;
                  return (
                    <View key={index} style={styles.barContainer}>
                      <View style={styles.barWrapper}>
                        <View
                          style={[
                            styles.bar,
                            {
                              height: `${Math.max(heightPct, 3)}%`,
                              backgroundColor: isToday ? colors.primary : colors.primaryLight + '60',
                            },
                          ]}
                        />
                      </View>
                      <Text style={[styles.barLabel, { color: colors.textMuted }]}>
                        {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' }).charAt(0)}
                      </Text>
                    </View>
                  );
                })}
              </View>
            </GlassCard>
          </View>
        )}

        {/* ── AI Insights ── */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
            <Text style={[styles.sectionAccent, { color: colors.primary }]}>│</Text> AI Insights
          </Text>
          <AICard
            icon="📈"
            title="Peak hour approaching"
            description="Orders expected to increase significantly. Consider preparing extra stock."
            severity="warning"
            action={{ label: 'View Details', onPress: () => navigateTo('AI') }}
            confidence={0.92}
          />
          <View style={{ height: 8 }} />
          <AICard
            icon="📦"
            title="Monitor your inventory"
            description="Keep an eye on stock levels for your popular items before peak hours."
            severity="info"
            action={{ label: 'Check Inventory', onPress: () => {} }}
            confidence={0.85}
          />
        </View>

        {/* ── Quick Actions ── */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
            <Text style={[styles.sectionAccent, { color: colors.primary }]}>│</Text> Quick Actions
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quickActionsRow}>
            {[
              { icon: '📊', label: 'Analytics', screen: 'Analytics', color: colors.secondary },
              { icon: '🧠', label: 'AI Insights', screen: 'AI', color: colors.aiPrimary },
              { icon: '📋', label: 'Orders', screen: 'Orders', color: colors.info },
              { icon: '🍽️', label: 'Menu', screen: 'Menu', color: colors.success },
              { icon: '🎯', label: 'Promotions', screen: 'Promotions', color: colors.warning },
              { icon: '💰', label: 'Settlements', screen: 'Settlements', color: colors.success },
              { icon: '👥', label: 'Staff', screen: 'StaffManagement', color: colors.secondary },
              { icon: '⏰', label: 'Slots', screen: 'SlotManagement', color: colors.info },
            ].map((item, i) => (
              <TouchableOpacity
                key={i}
                style={[styles.quickActionCard, { backgroundColor: colors.bgCard }]}
                onPress={() => navigateTo(item.screen)}
                activeOpacity={0.8}
              >
                <View style={[styles.quickActionIcon, { backgroundColor: item.color + '15' }]}>
                  <Text style={styles.quickActionEmoji}>{item.icon}</Text>
                </View>
                <Text style={[styles.quickActionLabel, { color: colors.textPrimary }]} numberOfLines={1}>{item.label}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* ── Recent Orders ── */}
        {data?.recent_orders && data.recent_orders.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeaderRow}>
              <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
                <Text style={[styles.sectionAccent, { color: colors.primary }]}>│</Text> Recent Orders
              </Text>
              <TouchableOpacity onPress={() => navigateTo('Orders')}>
                <Text style={[styles.seeAllText, { color: colors.primary }]}>See All →</Text>
              </TouchableOpacity>
            </View>
            {data.recent_orders.slice(0, 4).map((order: any) => (
              <TouchableOpacity key={order.id} onPress={() => navigateTo('Orders')} activeOpacity={0.8}>
                <GlassCard style={styles.recentOrderCard} padding={14} borderRadius={16}>
                  <View style={styles.recentOrderRow}>
                    <View style={styles.recentOrderLeft}>
                      <StatusPill
                        label={ORDER_STATUS[order.status]?.label || order.status}
                        variant={ORDER_STATUS[order.status]?.variant || 'neutral'}
                        size="sm"
                      />
                      <View>
                        <Text style={[styles.recentOrderId, { color: colors.textPrimary }]}>Order #{order.id}</Text>
                        <Text style={[styles.recentOrderMeta, { color: colors.textMuted }]}>
                          {formatPaise(order.total_amount)} • {new Date(order.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </Text>
                      </View>
                    </View>
                    <Text style={[styles.recentOrderArrow, { color: colors.textMuted }]}>›</Text>
                  </View>
                </GlassCard>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* ── Notifications ── */}
        {data?.recent_notifications && data.recent_notifications.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeaderRow}>
              <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
                <Text style={[styles.sectionAccent, { color: colors.primary }]}>│</Text> Notifications
              </Text>
              <TouchableOpacity onPress={() => navigateTo('Notifications')}>
                <Text style={[styles.seeAllText, { color: colors.primary }]}>See All →</Text>
              </TouchableOpacity>
            </View>
            {data.recent_notifications.slice(0, 2).map((n: any) => (
              <TouchableOpacity key={n.id} activeOpacity={0.8}>
                <GlassCard style={styles.notifCard} padding={14} borderRadius={16} intensity="medium">
                  <View style={styles.notifRow}>
                    <View style={[styles.notifDot, !n.is_read && { backgroundColor: colors.primary }, n.is_read && { backgroundColor: colors.textMuted }]} />
                    <View style={styles.notifContent}>
                      <Text style={[styles.notifTitle, { color: colors.textPrimary }]}>{n.title}</Text>
                      <Text style={[styles.notifMessage, { color: colors.textSecondary }]} numberOfLines={1}>{n.message}</Text>
                    </View>
                  </View>
                </GlassCard>
              </TouchableOpacity>
            ))}
          </View>
        )}

        <View style={[styles.bottomSpacer, { height: 100 }]} />
      </Animated.View>
    </ScrollView>
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
    paddingBottom: 36,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    overflow: 'hidden',
    ...shadows.header,
  },
  headerDeco1: {
    position: 'absolute',
    top: -40,
    right: -30,
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  headerDeco2: {
    position: 'absolute',
    bottom: -30,
    left: -60,
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  headerContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  headerLeft: { flex: 1 },
  greeting: { fontSize: 14, color: 'rgba(255,255,255,0.7)', fontWeight: '500' },
  vendorName: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3, marginBottom: 8 },
  headerStatusRow: { flexDirection: 'row', gap: 8 },
  headerRight: { alignItems: 'flex-end', gap: 8 },
  notifBell: { backgroundColor: 'rgba(255,255,255,0.15)', width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  bellIcon: { fontSize: 18 },
  headerDate: { fontSize: 12, color: 'rgba(255,255,255,0.6)', fontWeight: '500' },

  healthSection: { paddingHorizontal: spacing.lg, marginTop: spacing.md, marginBottom: spacing.md },
  healthRow: { flexDirection: 'row', alignItems: 'center' },
  healthInfo: { flex: 1, marginLeft: 16 },
  healthTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  healthSubtitle: { fontSize: 12, color: colors.textMuted, marginTop: 2, marginBottom: 10 },
  healthStats: { flexDirection: 'row', gap: 16 },
  healthStat: { alignItems: 'center' },
  healthStatValue: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  healthStatLabel: { fontSize: 10, color: colors.textMuted, fontWeight: '500', marginTop: 2 },

  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: spacing.lg, gap: spacing.md, marginBottom: spacing.md },

  section: { paddingHorizontal: spacing.lg, marginBottom: spacing.md },
  sectionHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.md },
  sectionAccent: { color: colors.primary, fontSize: 18 },
  seeAllText: { fontSize: 14, color: colors.primary, fontWeight: '600', marginBottom: spacing.md },

  orderStatusGrid: { flexDirection: 'row', gap: spacing.sm },
  orderStatusCard: {
    flex: 1, backgroundColor: colors.bgCard, borderRadius: 20, padding: 12, alignItems: 'center', ...shadows.card,
  },
  orderStatusIcon: { width: 36, height: 36, borderRadius: 12, justifyContent: 'center', alignItems: 'center', marginBottom: 6 },
  orderStatusEmoji: { fontSize: 18 },
  orderStatusLabel: { fontSize: 10, color: colors.textMuted, fontWeight: '600', marginTop: 2 },

  revenueChart: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', minHeight: 140, paddingTop: spacing.md },
  barContainer: { flex: 1, alignItems: 'center', marginHorizontal: 2 },
  barWrapper: { height: 80, justifyContent: 'flex-end', alignItems: 'center', width: '100%' },
  bar: { width: '70%', borderRadius: 6, minHeight: 3 },
  barLabel: { fontSize: 10, color: colors.textMuted, fontWeight: '600', marginTop: 4 },

  quickActionsRow: { gap: spacing.md, paddingRight: spacing.lg },
  quickActionCard: { backgroundColor: colors.bgCard, borderRadius: 20, paddingVertical: spacing.lg, paddingHorizontal: 12, alignItems: 'center', minWidth: 90, ...shadows.card },
  quickActionIcon: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center', marginBottom: 8 },
  quickActionEmoji: { fontSize: 22 },
  quickActionLabel: { fontSize: 12, fontWeight: '600', color: colors.textPrimary },

  recentOrderCard: { marginBottom: 6 },
  recentOrderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  recentOrderLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  recentOrderId: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  recentOrderMeta: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  recentOrderArrow: { fontSize: 24, color: colors.textMuted },

  notifCard: { marginBottom: 6 },
  notifRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  notifDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.textMuted },
  notifUnread: { backgroundColor: colors.primary },
  notifContent: { flex: 1 },
  notifTitle: { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  notifMessage: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },

  bottomSpacer: { height: spacing.huge },
});

