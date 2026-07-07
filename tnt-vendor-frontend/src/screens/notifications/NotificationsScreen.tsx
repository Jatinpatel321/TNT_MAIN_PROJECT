// ─── Notifications Inbox ──────────────────────────────────────────
// Premium notification center with priority grouping, filters, and AI

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { notificationApi, type Notification } from '../../services/notificationApi';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Badge from '../../design-system/components/Badge';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';

type FilterType = 'all' | 'unread' | 'order' | 'delay' | 'system';

const notificationIcons: Record<string, string> = {
  order_ready: '✅',
  order_accepted: '📋',
  order_preparing: '👨‍🍳',
  delay_alert: '⚠️',
  order_cancelled: '❌',
  pickup_reminder: '🔔',
  promo: '🎉',
  inventory: '📦',
  system: '🔧',
  default: '📢',
};

const notificationColors: Record<string, string> = {
  order_ready: colors.success,
  order_accepted: colors.primary,
  order_preparing: colors.warning,
  delay_alert: colors.error,
  order_cancelled: colors.error,
  pickup_reminder: colors.info,
  promo: colors.secondary,
  inventory: colors.success,
  system: colors.textMuted,
  default: colors.info,
};

export default function NotificationsScreen({ navigation }: any) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');
  const { user } = useAuth();
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    loadNotifications();
    loadUnreadCount();
  }, []);

  const loadNotifications = async () => {
    try {
      const response = await notificationApi.getNotifications();
      setNotifications(response.data);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadUnreadCount = async () => {
    try {
      const response = await notificationApi.getUnreadCount();
      setUnreadCount(response.data.unread_count);
    } catch (error) {
      console.error('Failed to load unread count:', error);
    }
  };

  const handlePress = async (notification: Notification) => {
    if (!notification.is_read) {
      try {
        await notificationApi.markAsRead(notification.id);
        setNotifications(prev => prev.map(n => n.id === notification.id ? { ...n, is_read: true } : n));
        setUnreadCount(prev => Math.max(0, prev - 1));
      } catch (error) {
        console.error('Failed to mark as read:', error);
      }
    }
    navigation.navigate('NotificationDetail', { notification });
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationApi.markAllAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const filtered = notifications.filter(n => {
    if (activeFilter === 'unread') return !n.is_read;
    if (activeFilter === 'order') return n.notification_type.includes('order');
    if (activeFilter === 'delay') return n.notification_type === 'delay_alert';
    if (activeFilter === 'system') return n.notification_type === 'system' || n.notification_type === 'inventory';
    return true;
  });

  const renderItem = ({ item }: { item: Notification }) => {
    const icon = notificationIcons[item.notification_type] || notificationIcons.default;
    const color = notificationColors[item.notification_type] || notificationColors.default;

    return (
      <TouchableOpacity
        activeOpacity={0.7}
        onPress={() => handlePress(item)}
      >
        <GlassCard
          padding={14}
          borderRadius={16}
          intensity={item.is_read ? 'light' : 'medium'}
          style={{ ...styles.notifCard, ...(!item.is_read ? styles.unreadCard : {}) } as any}
        >
          <View style={styles.notifRow}>
            <View style={[styles.iconCircle, { backgroundColor: `${color}15` }]}>
              <Text style={styles.notifIcon}>{icon}</Text>
            </View>
            <View style={styles.notifContent}>
              <View style={styles.notifHeader}>
                <Text style={[styles.notifTitle, !item.is_read && styles.unreadTitle]} numberOfLines={1}>
                  {item.title}
                </Text>
                {!item.is_read && <View style={[styles.unreadDot, { backgroundColor: color }]} />}
              </View>
              <Text style={styles.notifMessage} numberOfLines={2}>{item.message}</Text>
              <Text style={styles.notifTime}>
                {new Date(item.created_at).toLocaleString()}
              </Text>
            </View>
          </View>
        </GlassCard>
      </TouchableOpacity>
    );
  };

  const filters: { key: FilterType; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'unread', label: `Unread (${unreadCount})` },
    { key: 'order', label: 'Orders' },
    { key: 'delay', label: 'Delays' },
    { key: 'system', label: 'System' },
  ];

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading notifications...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <View style={styles.headerRow}>
          <Text style={styles.headerTitle}>Notifications</Text>
          {unreadCount > 0 && (
            <TouchableOpacity style={styles.markAllButton} onPress={handleMarkAllRead}>
              <Text style={styles.markAllText}>Mark all read</Text>
            </TouchableOpacity>
          )}
        </View>
        <Text style={styles.headerSubtitle}>
          {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
        </Text>
      </View>

      {/* Filter Chips */}
      <FlatList
        horizontal
        data={filters}
        keyExtractor={f => f.key}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filterRow}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.filterChip, activeFilter === item.key && styles.filterChipActive]}
            onPress={() => setActiveFilter(item.key)}
          >
            <Text style={[styles.filterText, activeFilter === item.key && styles.filterTextActive]} numberOfLines={1}>
              {item.label}
            </Text>
          </TouchableOpacity>
        )}
      />

      {/* List */}
      <FlatList
        data={filtered}
        keyExtractor={item => item.id.toString()}
        renderItem={renderItem}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <PremiumEmptyState
            icon="🔔"
            title="No notifications"
            description={activeFilter === 'unread' ? 'You\'re all caught up!' : 'No notifications match this filter.'}
          />
        }
      />
    </View>
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
    overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  markAllButton: { backgroundColor: 'rgba(255,255,255,0.15)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10 },
  markAllText: { fontSize: 12, fontWeight: '600', color: colors.textInverse },
  filterRow: { paddingHorizontal: spacing.lg, paddingVertical: spacing.md, gap: 8 },
  filterChip: {
    paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20,
    backgroundColor: colors.bgCard, borderWidth: 1.5, borderColor: colors.border, marginRight: 8, ...shadows.sm,
  },
  filterChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  filterText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary },
  filterTextActive: { color: colors.textInverse },
  listContent: { padding: spacing.lg, paddingBottom: spacing.huge },
  notifCard: { marginBottom: spacing.sm },
  unreadCard: { borderLeftWidth: 4, borderLeftColor: colors.primary },
  notifRow: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  iconCircle: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  notifIcon: { fontSize: 20 },
  notifContent: { flex: 1 },
  notifHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  notifTitle: { fontSize: 15, fontWeight: '600', color: colors.textPrimary, flex: 1 },
  unreadTitle: { fontWeight: '700' },
  unreadDot: { width: 8, height: 8, borderRadius: 4 },
  notifMessage: { fontSize: 13, color: colors.textSecondary, marginTop: 4, lineHeight: 18 },
  notifTime: { fontSize: 11, color: colors.textMuted, marginTop: 4 },
});
