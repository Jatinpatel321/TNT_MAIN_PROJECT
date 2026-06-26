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
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { vendorApi } from '../../services/vendorApi';

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

export default function DashboardScreen({ navigation }: any) {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchDashboardData = async (isRefresh = false) => {
    try {
      if (!isRefresh) {
        setLoading(true);
      }
      setError(null);
      
      const response = await vendorApi.getDashboardMetrics();
      setMetrics(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchDashboardData(true);
  }, []);

  const handleRetry = () => {
    fetchDashboardData();
  };

  const navigateToAnalytics = () => {
    navigation.navigate('Analytics');
  };

  const navigateToMenu = () => {
    navigation.navigate('Menu');
  };

  const navigateToOrders = () => {
    navigation.navigate('Orders');
  };

  const navigateToDemand = () => {
    navigation.navigate('DemandDashboard');
  };

  const navigateToNotificationDetail = (notificationId: number) => {
    navigation.navigate('NotificationDetail', { notificationId });
  };

  // Loading State
  if (loading) {
    return (
      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.greeting}>Welcome back,</Text>
          <Text style={styles.vendorName}>{user?.vendor_name || 'Vendor'}</Text>
        </View>
        <View style={styles.statsGrid}>
          {[1, 2, 3, 4].map((item) => (
            <View key={item} style={styles.statCard}>
              <ActivityIndicator size="small" color="#10B981" />
              <View style={styles.skeletonText} />
            </View>
          ))}
        </View>
        <View style={styles.section}>
          <View style={styles.skeletonSection} />
          <View style={styles.skeletonSection} />
        </View>
      </ScrollView>
    );
  }

  // Error State
  if (error && !metrics) {
    return (
      <ScrollView
        style={styles.container}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.header}>
          <Text style={styles.greeting}>Welcome back,</Text>
          <Text style={styles.vendorName}>{user?.vendor_name || 'Vendor'}</Text>
        </View>
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={handleRetry}>
            <Text style={styles.retryButtonText}>Retry</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.greeting}>Welcome back,</Text>
        <Text style={styles.vendorName}>{user?.vendor_name || 'Vendor'}</Text>
      </View>

      {/* Stats Grid */}
      <View style={styles.statsGrid}>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{metrics?.orders_today || 0}</Text>
          <Text style={styles.statLabel}>Orders Today</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>₹{metrics?.revenue_today || 0}</Text>
          <Text style={styles.statLabel}>Revenue Today</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{metrics?.pending_orders || 0}</Text>
          <Text style={styles.statLabel}>Pending Orders</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{metrics?.completed_orders || 0}</Text>
          <Text style={styles.statLabel}>Completed Orders</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>⭐ {metrics?.avg_rating || 0}</Text>
          <Text style={styles.statLabel}>Rating</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{metrics?.active_slots || 0}</Text>
          <Text style={styles.statLabel}>Active Slots</Text>
        </View>
      </View>

      {/* Quick Actions */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <TouchableOpacity style={styles.actionCard} onPress={navigateToAnalytics}>
          <Text style={styles.actionText}>📊 View Analytics</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionCard} onPress={navigateToDemand}>
          <Text style={styles.actionText}>Smart Demand Dashboard</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionCard} onPress={navigateToMenu}>
          <Text style={styles.actionText}>🍽️ Update Menu</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionCard} onPress={navigateToOrders}>
          <Text style={styles.actionText}>📦 View Orders</Text>
        </TouchableOpacity>
      </View>

      {/* Recent Orders Widget */}
      {metrics?.recent_orders && metrics.recent_orders.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Orders</Text>
          {metrics.recent_orders.slice(0, 3).map((order) => (
            <TouchableOpacity
              key={order.id}
              style={styles.widgetCard}
              onPress={() => navigateToOrders()}
            >
              <View style={styles.widgetHeader}>
                <Text style={styles.widgetTitle}>Order #{order.id}</Text>
                <View style={[
                  styles.statusBadge,
                  { backgroundColor: getStatusColor(order.status) }
                ]}>
                  <Text style={styles.statusText}>{order.status}</Text>
                </View>
              </View>
              <Text style={styles.widgetSubtext}>
                ₹{order.total_amount} • {new Date(order.created_at).toLocaleTimeString()}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Recent Notifications Widget */}
      {metrics?.recent_notifications && metrics.recent_notifications.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Notifications</Text>
          {metrics.recent_notifications.slice(0, 3).map((notification) => (
            <TouchableOpacity
              key={notification.id}
              style={[
                styles.widgetCard,
                !notification.is_read && styles.unreadWidget
              ]}
              onPress={() => navigateToNotificationDetail(notification.id)}
            >
              <View style={styles.widgetHeader}>
                <Text style={styles.widgetTitle}>{notification.title}</Text>
                {!notification.is_read && <View style={styles.unreadDot} />}
              </View>
              <Text style={styles.widgetSubtext} numberOfLines={2}>
                {notification.message}
              </Text>
              <Text style={styles.widgetTime}>
                {new Date(notification.created_at).toLocaleTimeString()}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Revenue Trend Widget */}
      {metrics?.revenue_trend && metrics.revenue_trend.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Revenue Trend (7 Days)</Text>
          <View style={styles.revenueChart}>
            {metrics.revenue_trend.map((day, index) => (
              <View key={index} style={styles.revenueBarContainer}>
                <View style={styles.revenueBarWrapper}>
                  <View
                    style={[
                      styles.revenueBar,
                      {
                        height: `${Math.min((day.revenue / Math.max(...metrics.revenue_trend.map(d => d.revenue))) * 100, 100)}%`,
                      },
                    ]}
                  />
                </View>
                <Text style={styles.revenueLabel}>
                  {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}
                </Text>
                <Text style={styles.revenueValue}>₹{day.revenue}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {error && metrics && (
        <View style={styles.inlineError}>
          <Text style={styles.inlineErrorText}>{error}</Text>
          <TouchableOpacity onPress={handleRetry}>
            <Text style={styles.inlineRetryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
}

function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'placed':
      return '#F59E0B';
    case 'confirmed':
      return '#3B82F6';
    case 'preparing':
      return '#8B5CF6';
    case 'ready':
      return '#10B981';
    case 'picked':
    case 'completed':
      return '#059669';
    case 'cancelled':
      return '#EF4444';
    default:
      return '#6B7280';
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#10B981',
  },
  greeting: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  vendorName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
    marginTop: 4,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 16,
    gap: 12,
  },
  statCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#10B981',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 12,
  },
  actionCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  actionText: {
    fontSize: 16,
    color: '#374151',
  },
  widgetCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  unreadWidget: {
    borderLeftWidth: 4,
    borderLeftColor: '#10B981',
  },
  widgetHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  widgetTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    flex: 1,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 12,
    color: 'white',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  widgetSubtext: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  widgetTime: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 4,
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#10B981',
    marginLeft: 8,
  },
  revenueChart: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    minHeight: 200,
  },
  revenueBarContainer: {
    flex: 1,
    alignItems: 'center',
    marginHorizontal: 4,
  },
  revenueBarWrapper: {
    height: 150,
    justifyContent: 'flex-end',
    alignItems: 'center',
    width: '100%',
  },
  revenueBar: {
    width: '80%',
    backgroundColor: '#10B981',
    borderRadius: 4,
    minHeight: 4,
  },
  revenueLabel: {
    fontSize: 10,
    color: '#6B7280',
    marginTop: 4,
    textAlign: 'center',
  },
  revenueValue: {
    fontSize: 10,
    color: '#10B981',
    fontWeight: '600',
    marginTop: 2,
    textAlign: 'center',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
    marginTop: 100,
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  errorText: {
    fontSize: 16,
    color: '#EF4444',
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    backgroundColor: '#10B981',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  inlineError: {
    backgroundColor: '#FEE2E2',
    padding: 12,
    borderRadius: 8,
    margin: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  inlineErrorText: {
    color: '#EF4444',
    fontSize: 14,
    flex: 1,
  },
  inlineRetryText: {
    color: '#EF4444',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 12,
  },
  skeletonText: {
    width: 40,
    height: 20,
    backgroundColor: '#E5E7EB',
    borderRadius: 4,
    marginTop: 8,
  },
  skeletonSection: {
    height: 120,
    backgroundColor: '#E5E7EB',
    borderRadius: 12,
    marginBottom: 12,
  },
});