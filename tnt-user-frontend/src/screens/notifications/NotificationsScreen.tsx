import React, {useCallback, useEffect, useRef, useState} from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  View,
} from 'react-native';
import {Text} from 'react-native-paper';
import {NativeStackScreenProps} from '@react-navigation/native-stack';

import type {AppTabsParamList} from '../../types/navigation';
import type {NotificationItem, NotificationTypeKey} from '../../types/models';
import {Screen} from '../../components/Screen';
import {NotificationCard} from '../../components/NotificationCard';
import {
  getNotifications,
  getUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
} from '../../services/notificationService';
import {toApiError} from '../../services/apiClient';

type Props = NativeStackScreenProps<AppTabsParamList, 'NotificationsTab'>;

type FilterTab = 'all' | 'unread' | 'orders' | 'alerts';

const FILTER_TABS: {key: FilterTab; label: string}[] = [
  {key: 'all', label: 'All'},
  {key: 'unread', label: 'Unread'},
  {key: 'orders', label: 'Orders'},
  {key: 'alerts', label: 'Alerts'},
];

const ORDER_TYPES: NotificationTypeKey[] = [
  'order_placed',
  'order_accepted',
  'order_preparing',
  'order_ready',
  'order_cancelled',
];
const ALERT_TYPES: NotificationTypeKey[] = [
  'pickup_reminder',
  'delay_alert',
];

export function NotificationsScreen({navigation}: Props) {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [unreadCount, setUnreadCount] = useState(0);
  const [markingAll, setMarkingAll] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const [list, count] = await Promise.all([
        getNotifications(),
        getUnreadCount(),
      ]);
      setItems(list);
      setUnreadCount(count);
    } catch (e) {
      Alert.alert('Failed to load notifications', toApiError(e).message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    intervalRef.current = setInterval(load, 30000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [load]);

  const onPress = async (id: number) => {
    try {
      const updated = await markNotificationRead(id);
      setItems(prev =>
        prev.map(n => (n.id === id ? {...n, ...updated} : n)),
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (e) {
      Alert.alert('Update failed', toApiError(e).message);
    }
  };

  const onMarkAllRead = async () => {
    try {
      setMarkingAll(true);
      const res = await markAllNotificationsRead();
      setItems(prev => prev.map(n => ({...n, is_read: true})));
      setUnreadCount(0);
      Alert.alert('Done', `${res.updated_count} notifications marked as read.`);
    } catch (e) {
      Alert.alert('Failed', toApiError(e).message);
    } finally {
      setMarkingAll(false);
    }
  };

  const filtered = items.filter(item => {
    if (activeTab === 'unread') return !item.is_read;
    if (activeTab === 'orders')
      return ORDER_TYPES.includes(item.notification_type);
    if (activeTab === 'alerts')
      return ALERT_TYPES.includes(item.notification_type);
    return true;
  });

  return (
    <Screen>
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.title}>Notifications</Text>
          {unreadCount > 0 && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>
                {unreadCount > 99 ? '99+' : unreadCount}
              </Text>
            </View>
          )}
        </View>
        {unreadCount > 0 && (
          <Pressable
            onPress={onMarkAllRead}
            disabled={markingAll}
            style={styles.markAllBtn}>
            <Text style={styles.markAllText}>
              {markingAll ? 'Marking...' : 'Mark all read'}
            </Text>
          </Pressable>
        )}
      </View>

      <View style={styles.tabRow}>
        {FILTER_TABS.map(tab => (
          <Pressable
            key={tab.key}
            onPress={() => setActiveTab(tab.key)}
            style={[styles.tab, activeTab === tab.key && styles.tabActive]}>
            <Text
              style={[
                styles.tabLabel,
                activeTab === tab.key && styles.tabLabelActive,
              ]}>
              {tab.label}
              {tab.key === 'unread' && unreadCount > 0
                ? ` (${unreadCount})`
                : ''}
            </Text>
          </Pressable>
        ))}
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator />
        </View>
      ) : filtered.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>
            {activeTab === 'unread' ? '✓' : '🔔'}
          </Text>
          <Text style={styles.emptyTitle}>
            {activeTab === 'unread'
              ? "You're all caught up"
              : activeTab === 'orders'
                ? 'No order updates'
                : activeTab === 'alerts'
                  ? 'No alerts right now'
                  : 'No notifications yet'}
          </Text>
          <Text style={styles.emptySub}>
            {activeTab === 'all'
              ? "We'll notify you when something comes up."
              : 'Check back later for updates.'}
          </Text>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={item => String(item.id)}
          renderItem={({item}) => (
            <NotificationCard item={item} onPress={() => onPress(item.id)} />
          )}
          ItemSeparatorComponent={() => <View style={{height: 8}} />}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                load();
              }}
            />
          }
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingVertical: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
  },
  badge: {
    backgroundColor: '#EF4444',
    borderRadius: 10,
    paddingHorizontal: 7,
    paddingVertical: 2,
    minWidth: 20,
    alignItems: 'center',
  },
  badgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '800',
  },
  markAllBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#EFF6FF',
  },
  markAllText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#2563EB',
  },
  tabRow: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: 12,
  },
  tab: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    backgroundColor: '#F3F4F6',
  },
  tabActive: {
    backgroundColor: '#DBEAFE',
  },
  tabLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
  },
  tabLabelActive: {
    color: '#1D4ED8',
    fontWeight: '700',
  },
  center: {
    paddingVertical: 40,
    alignItems: 'center',
  },
  emptyState: {
    alignItems: 'center',
    paddingTop: 48,
    paddingHorizontal: 24,
  },
  emptyIcon: {
    fontSize: 40,
    marginBottom: 8,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#111827',
    marginBottom: 4,
  },
  emptySub: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
  },
  list: {
    paddingBottom: 16,
  },
});
