import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
  Dimensions,
  Animated,
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { vendorApi } from '../../services/vendorApi';
import { Colors, Typography, Spacing, Shadows, BorderRadius } from '../../theme';
import Card from '../../components/Card';
import MetricCard from '../../components/MetricCard';
import Badge from '../../components/Badge';
import Button from '../../components/Button';

const { width } = Dimensions.get('window');

interface DashboardMetrics {
  orders_today: number;
  revenue_today: number;
  pending_orders: number;
  completed_orders: number;
  avg_rating: number;
  active_slots: number;
  recent_orders: any[];
  recent_notifications: any[];
  revenue_trend: { date: string; revenue: number }[];
}

type StatusKey = 'placed' | 'pending' | 'confirmed' | 'preparing' | 'ready' | 'ready_for_pickup' | 'completed' | 'picked' | 'cancelled';

const STATUS_MAP: Record<string, StatusKey> = {
  placed: 'placed',
  pending: 'pending',
  confirmed: 'confirmed',
  preparing: 'preparing',
  ready: 'ready',
  ready_for_pickup: 'ready_for_pickup',
  completed: 'completed',
  picked: 'picked',
  cancelled: 'cancelled',
};

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

function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    placed: '#8B5CF6',
    pending: '#8B5CF6',
    confirmed: '#3B82F6',
    preparing: '#F59E0B',
    ready: '#10B981',
    ready_for_pickup: '#10B981',
    completed: '#059669',
    picked: '#6B7280',
    cancelled: '#EF4444',
  };
  return map[STATUS_MAP[status] || status] || '#6B7280';
}

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    placed: 'Placed',
    pending: 'Pending',
    confirmed: 'Confirmed',
    preparing: 'Preparing',
    ready: 'Ready',
    ready_for_pickup: 'Ready',
    completed: 'Completed',
    picked: 'Picked Up',
    cancelled: 'Cancelled',
  };
  return map[status] || status;
}

export default function DashboardScreen({ navigation }: any) {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Entrance animation
  const fadeAnim = React.useRef(new Animated.Value(0)).current;
  const slideAnim = React.useRef(new Animated.Value(20)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 400,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const fetchDashboardData = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      setError(null);
      const response = await vendorApi.getDashboardMetrics();
      setMetrics(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchDashboardData(); }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchDashboardData(true);
  }, []);

  const handleRetry = () => fetchDashboardData();

  const navigateTo = (screen: string) => navigation.navigate(screen);

  // Loading State
  if (loading) {
    return (
      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <View style={styles.headerDeco1} />
          <View style={styles.headerDeco2} />
          <View style={styles.headerContent}>
            <View>
              <Text style={styles.greeting}>Welcome back,</Text>
              <Text style={styles.vendorName}>{user?.vendor_name || 'Vendor'}</Text>
            </View>
            <View style={styles.headerRight}>
              <Text style={styles.headerDate}>
                {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
              </Text>
            </View>
          </View>
        </View>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}><Text style={styles.sectionAccent}>│</Text> Today's Overview</Text>
          <View style={styles.statsGrid}>
            {[1, 2, 3, 4].map((item) => (
              <View key={item} style={styles.skeletonCard}>
                <ActivityIndicator size="small" color={Colors.primary} />
              </View>
            ))}
          </View>
        </View>
        <View style={styles.section}>
          <View style={styles.skeletonBlock} />
          <View style={styles.skeletonBlock} />
        </View>
      </ScrollView>
    );
  }

  // Error State
  if (error && !metrics) {
    return (
      <ScrollView style={styles.container}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <View style={styles.header}>
          <View style={styles.headerDeco1} />
          <View style={styles.headerDeco2} />
          <View style={styles.headerContent}>
            <View>
              <Text style={styles.greeting}>Welcome back,</Text>
              <Text style={styles.vendorName}>{user?.vendor_name || 'Vendor'}</Text>
            </View>
          </View>
        </View>
        <View style={styles.errorContainer}>
          <View style={styles.errorIconCircle}>
            <Text style={styles.errorIconText}>⚠️</Text>
          </View>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={handleRetry}>
            <Text style={styles.retryButtonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.white} />}
      showsVerticalScrollIndicator={false}
    >
      {/* ── Premium Header ── */}
      <View style={styles.header}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <View style={styles.headerContent}>
          <View>
            <Text style={styles.greeting}>Welcome back,</Text>
            <Text style={styles.vendorName}>{user?.vendor_name || 'Vendor'}</Text>
          </View>
          <View style={styles.headerRight}>
            <View style={styles.dateBadge}>
              <Text style={styles.headerDate}>
                {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
              </Text>
            </View>
            <View style={styles.ratingBadge}>
              <Text style={styles.ratingStar}>⭐</Text>
              <Text style={styles.ratingValue}>{metrics?.avg_rating?.toFixed(1) || '0.0'}</Text>
            </View>
          </View>
        </View>
      </View>

      <Animated.View style={{ opacity: fadeAnim, transform: [{ translateY: slideAnim }] }}>
        {/* ── Stats Grid ── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>
            <Text style={styles.sectionAccent}>│</Text> Today's Overview
          </Text>
          <View style={styles.statsGrid}>
            <MetricCard
              value={metrics?.orders_today ?? 0}
              label="Orders Today"
              icon="📦"
              color={Colors.primary}
              trend={metrics?.orders_today ? { value: 12, isUp: true } : undefined}
              style={styles.statCardItem}
            />
            <MetricCard
              value={`₹${metrics?.revenue_today ?? 0}`}
              label="Revenue Today"
              icon="💰"
              color={Colors.secondary}
              trend={metrics?.revenue_today ? { value: 8, isUp: true } : undefined}
              style={styles.statCardItem}
            />
            <MetricCard
              value={metrics?.pending_orders ?? 0}
              label="Pending"
              icon="⏳"
              color={Colors.warning}
              style={styles.statCardItem}
            />
            <MetricCard
              value={metrics?.completed_orders ?? 0}
              label="Completed"
              icon="✅"
              color={Colors.success}
              style={styles.statCardItem}
            />
            <MetricCard
              value={metrics?.active_slots ?? 0}
              label="Active Slots"
              icon="🕐"
              color={Colors.info}
              style={styles.statCardItem}
            />
            <MetricCard
              value={`⭐ ${metrics?.avg_rating?.toFixed(1) || '0.0'}`}
              label="Rating"
              icon="🌟"
              color={Colors.accent}
              style={styles.statCardItem}
            />
          </View>
        </View>

        {/* ── Quick Actions ── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>
            <Text style={styles.sectionAccent}>│</Text> Quick Actions
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quickActionsRow}>
            <TouchableOpacity style={styles.quickActionCard} onPress={() => navigateTo('Analytics')} activeOpacity={0.85}>
              <View style={[styles.quickActionIcon, { backgroundColor: Colors.secondaryPale }]}>
                <Text style={styles.quickActionEmoji}>📊</Text>
              </View>
              <Text style={styles.quickActionLabel}>Analytics</Text>
              <Text style={styles.quickActionDesc}>View insights</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quickActionCard} onPress={() => navigateTo('DemandDashboard')} activeOpacity={0.85}>
              <View style={[styles.quickActionIcon, { backgroundColor: Colors.accentPale }]}>
                <Text style={styles.quickActionEmoji}>🧠</Text>
              </View>
              <Text style={styles.quickActionLabel}>Demand</Text>
              <Text style={styles.quickActionDesc}>Smart predictions</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quickActionCard} onPress={() => navigateTo('Menu')} activeOpacity={0.85}>
              <View style={[styles.quickActionIcon, { backgroundColor: Colors.primaryPale }]}>
                <Text style={styles.quickActionEmoji}>🍽️</Text>
              </View>
              <Text style={styles.quickActionLabel}>Menu</Text>
              <Text style={styles.quickActionDesc}>Update items</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quickActionCard} onPress={() => navigateTo('Orders')} activeOpacity={0.85}>
              <View style={[styles.quickActionIcon, { backgroundColor: Colors.infoPale }]}>
                <Text style={styles.quickActionEmoji}>📋</Text>
              </View>
              <Text style={styles.quickActionLabel}>Orders</Text>
              <Text style={styles.quickActionDesc}>Manage orders</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quickActionCard} onPress={() => navigateTo('Promotions')} activeOpacity={0.85}>
              <View style={[styles.quickActionIcon, { backgroundColor: Colors.warningPale }]}>
                <Text style={styles.quickActionEmoji}>🎯</Text>
              </View>
              <Text style={styles.quickActionLabel}>Promos</Text>
              <Text style={styles.quickActionDesc}>Run campaigns</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.quickActionCard} onPress={() => navigateTo('Settlements')} activeOpacity={0.85}>
              <View style={[styles.quickActionIcon, { backgroundColor: Colors.successPale }]}>
                <Text style={styles.quickActionEmoji}>💳</Text>
              </View>
              <Text style={styles.quickActionLabel}>Settlements</Text>
              <Text style={styles.quickActionDesc}>View payouts</Text>
            </TouchableOpacity>
          </ScrollView>
        </View>

        {/* ── Recent Orders ── */}
        {metrics?.recent_orders && metrics.recent_orders.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeaderRow}>
              <Text style={styles.sectionTitle}>
                <Text style={styles.sectionAccent}>│</Text> Recent Orders
              </Text>
              <TouchableOpacity onPress={() => navigateTo('Orders')}>
                <Text style={styles.seeAllText}>See All →</Text>
              </TouchableOpacity>
            </View>
            {metrics.recent_orders.slice(0, 4).map((order) => {
              const status = order.status || '';
              const sk: StatusKey = STATUS_MAP[status] || 'placed';
              const statusColor = getStatusColor(status);
              return (
                <TouchableOpacity key={order.id} onPress={() => navigateTo('Orders')} activeOpacity={0.8}>
                  <Card variant="flat" style={styles.orderWidgetCard} padding={Spacing.lg}>
                    <View style={styles.orderWidgetRow}>
                      <View style={styles.orderWidgetLeft}>
                        <View style={[styles.orderStatusDot, { backgroundColor: statusColor }]} />
                        <View>
                          <View style={styles.orderWidgetTitleRow}>
                            <Text style={styles.orderWidgetId}>Order #{order.id}</Text>
                            <Badge label={getStatusLabel(status)} variant={statusToBadgeVariant[sk] || 'neutral'} size="sm" />
                          </View>
                          <Text style={styles.orderWidgetMeta}>
                            ₹{order.total_amount} • {new Date(order.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </Text>
                        </View>
                      </View>
                      <Text style={styles.orderWidgetArrow}>›</Text>
                    </View>
                  </Card>
                </TouchableOpacity>
              );
            })}
          </View>
        )}

        {/* ── Revenue Trend ── */}
        {metrics?.revenue_trend && metrics.revenue_trend.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              <Text style={styles.sectionAccent}>│</Text> Revenue Trend
            </Text>
            <Card variant="elevated" padding={Spacing.lg}>
              <View style={styles.revenueChart}>
                {metrics.revenue_trend.map((day, index) => {
                  const maxRev = Math.max(...metrics.revenue_trend.map(d => d.revenue), 1);
                  const heightPct = (day.revenue / maxRev) * 100;
                  return (
                    <View key={index} style={styles.revenueBarContainer}>
                      <Text style={styles.revenueBarValue}>₹{day.revenue}</Text>
                      <View style={styles.revenueBarWrapper}>
                        <View style={[styles.revenueBar, { height: `${Math.max(heightPct, 4)}%`, backgroundColor: index === metrics.revenue_trend.length - 1 ? Colors.primary : Colors.primaryLight }]} />
                      </View>
                      <Text style={styles.revenueBarLabel}>
                        {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' }).charAt(0)}
                      </Text>
                    </View>
                  );
                })}
              </View>
            </Card>
          </View>
        )}

        {/* ── Recent Notifications ── */}
        {metrics?.recent_notifications && metrics.recent_notifications.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeaderRow}>
              <Text style={styles.sectionTitle}>
                <Text style={styles.sectionAccent}>│</Text> Notifications
              </Text>
              <TouchableOpacity onPress={() => navigateTo('NotificationDetail')}>
                <Text style={styles.seeAllText}>See All →</Text>
              </TouchableOpacity>
            </View>
            {metrics.recent_notifications.slice(0, 3).map((notification) => (
              <TouchableOpacity key={notification.id} activeOpacity={0.8}>
                <Card variant="flat" style={[styles.notifWidgetCard, !notification.is_read ? styles.notifUnread : undefined]} padding={Spacing.lg}>
                  <View style={styles.notifWidgetRow}>
                    <View style={styles.notifWidgetLeft}>
                      {!notification.is_read && <View style={styles.notifUnreadDot} />}
                      <View style={styles.notifContent}>
                        <Text style={styles.notifTitle}>{notification.title}</Text>
                        <Text style={styles.notifMessage} numberOfLines={1}>{notification.message}</Text>
                        <Text style={styles.notifTime}>
                          {new Date(notification.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </Text>
                      </View>
                    </View>
                    <Text style={styles.notifArrow}>›</Text>
                  </View>
                </Card>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {error && metrics && (
          <View style={styles.inlineError}>
            <Text style={styles.inlineErrorText}>⚠️ {error}</Text>
            <TouchableOpacity onPress={handleRetry}>
              <Text style={styles.inlineRetryText}>Retry</Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={styles.bottomSpacer} />
      </Animated.View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
  },

  // ── Premium Header ──
  header: {
    backgroundColor: Colors.primary,
    paddingTop: Spacing.xxl + 24,
    paddingBottom: Spacing.xxl,
    paddingHorizontal: Spacing.xl,
    borderBottomLeftRadius: BorderRadius.xl,
    borderBottomRightRadius: BorderRadius.xl,
    overflow: 'hidden',
    ...Shadows.header,
  },
  headerDeco1: {
    position: 'absolute',
    top: -40,
    right: -30,
    width: 160,
    height: 160,
    borderRadius: 80,
    backgroundColor: Colors.white + '12',
  },
  headerDeco2: {
    position: 'absolute',
    bottom: -20,
    left: -50,
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: Colors.white + '08',
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  greeting: {
    fontSize: Typography.bodySmall,
    color: Colors.textInverse + 'CC',
    fontWeight: Typography.medium,
  },
  vendorName: {
    fontSize: Typography.h2,
    fontWeight: Typography.bold,
    color: Colors.textInverse,
    marginTop: 2,
  },
  headerRight: {
    alignItems: 'flex-end',
    gap: Spacing.sm,
  },
  dateBadge: {
    backgroundColor: Colors.white + '20',
    borderRadius: BorderRadius.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs + 2,
  },
  headerDate: {
    fontSize: Typography.caption,
    color: Colors.textInverse + 'DD',
    fontWeight: Typography.semibold,
  },
  ratingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: Colors.accent + '30',
    borderRadius: BorderRadius.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs + 2,
  },
  ratingStar: {
    fontSize: 12,
  },
  ratingValue: {
    fontSize: Typography.caption,
    color: Colors.textInverse,
    fontWeight: Typography.bold,
  },

  // ── Sections ──
  section: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.xl,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  sectionTitle: {
    fontSize: Typography.h4,
    fontWeight: Typography.bold,
    color: Colors.textPrimary,
    marginBottom: Spacing.md,
  },
  sectionAccent: {
    color: Colors.primary,
    fontSize: Typography.h3,
    marginRight: Spacing.sm,
  },
  seeAllText: {
    fontSize: Typography.bodySmall,
    color: Colors.primary,
    fontWeight: Typography.semibold,
    marginBottom: Spacing.md,
  },

  // ── Stats Grid ──
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  statCardItem: {
    flex: 1,
    minWidth: '30%',
  },

  // ── Quick Actions ──
  quickActionsRow: {
    gap: Spacing.md,
    paddingRight: Spacing.lg,
  },
  quickActionCard: {
    backgroundColor: Colors.bgCard,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    alignItems: 'center',
    width: 110,
    ...Shadows.card,
  },
  quickActionIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  quickActionEmoji: {
    fontSize: 22,
  },
  quickActionLabel: {
    fontSize: Typography.bodySmall,
    fontWeight: Typography.semibold,
    color: Colors.textPrimary,
  },
  quickActionDesc: {
    fontSize: Typography.tiny,
    color: Colors.textMuted,
    marginTop: 2,
  },

  // ── Order Widget ──
  orderWidgetCard: {
    marginBottom: Spacing.sm,
  },
  orderWidgetRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  orderWidgetLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: Spacing.sm,
  },
  orderStatusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  orderWidgetTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  orderWidgetId: {
    fontSize: Typography.bodySmall,
    fontWeight: Typography.semibold,
    color: Colors.textPrimary,
  },
  orderWidgetMeta: {
    fontSize: Typography.caption,
    color: Colors.textMuted,
    marginTop: 2,
  },
  orderWidgetArrow: {
    fontSize: Typography.h3,
    color: Colors.textMuted,
    marginLeft: Spacing.sm,
  },

  // ── Revenue Chart ──
  revenueChart: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    minHeight: 180,
    paddingTop: Spacing.md,
  },
  revenueBarContainer: {
    flex: 1,
    alignItems: 'center',
    marginHorizontal: 2,
  },
  revenueBarValue: {
    fontSize: Typography.tiny,
    color: Colors.textMuted,
    fontWeight: Typography.semibold,
    marginBottom: 4,
  },
  revenueBarWrapper: {
    height: 120,
    justifyContent: 'flex-end',
    alignItems: 'center',
    width: '100%',
  },
  revenueBar: {
    width: '70%',
    backgroundColor: Colors.primaryLight,
    borderRadius: BorderRadius.sm,
    minHeight: 3,
  },
  revenueBarLabel: {
    fontSize: Typography.tiny,
    color: Colors.textMuted,
    fontWeight: Typography.semibold,
    marginTop: 4,
  },

  // ── Notification Widget ──
  notifWidgetCard: {
    marginBottom: Spacing.sm,
  },
  notifUnread: {
    borderLeftWidth: 3,
    borderLeftColor: Colors.primary,
  },
  notifWidgetRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  notifWidgetLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: Spacing.md,
  },
  notifUnreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.primary,
  },
  notifContent: {
    flex: 1,
  },
  notifTitle: {
    fontSize: Typography.bodySmall,
    fontWeight: Typography.semibold,
    color: Colors.textPrimary,
  },
  notifMessage: {
    fontSize: Typography.caption,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  notifTime: {
    fontSize: Typography.tiny,
    color: Colors.textMuted,
    marginTop: 2,
  },
  notifArrow: {
    fontSize: Typography.h3,
    color: Colors.textMuted,
    marginLeft: Spacing.sm,
  },

  // ── Error States ──
  errorContainer: {
    alignItems: 'center',
    paddingVertical: Spacing.huge,
    paddingHorizontal: Spacing.xxl,
  },
  errorIconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: Colors.warningPale,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.lg,
  },
  errorIconText: {
    fontSize: 28,
  },
  errorText: {
    fontSize: Typography.body,
    color: Colors.error,
    textAlign: 'center',
    marginBottom: Spacing.xl,
    lineHeight: 22,
  },
  retryButton: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.xxl,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
    ...Shadows.button,
  },
  retryButtonText: {
    color: Colors.textInverse,
    fontSize: Typography.body,
    fontWeight: Typography.semibold,
  },
  inlineError: {
    backgroundColor: Colors.errorPale,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
    marginHorizontal: Spacing.lg,
    marginTop: Spacing.lg,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  inlineErrorText: {
    color: Colors.error,
    fontSize: Typography.caption,
    flex: 1,
  },
  inlineRetryText: {
    color: Colors.error,
    fontSize: Typography.caption,
    fontWeight: Typography.bold,
    marginLeft: Spacing.md,
  },

  // ── Skeleton ──
  skeletonCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: Colors.bgCard,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
    height: 80,
    ...Shadows.card,
  },
  skeletonBlock: {
    height: 100,
    backgroundColor: Colors.borderLight,
    borderRadius: BorderRadius.lg,
    marginBottom: Spacing.md,
  },

  bottomSpacer: {
    height: Spacing.huge,
  },
});
