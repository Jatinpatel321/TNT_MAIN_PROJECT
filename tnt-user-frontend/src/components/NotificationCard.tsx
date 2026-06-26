import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';
import {Text} from 'react-native-paper';

import type {NotificationItem, NotificationTypeKey} from '../types/models';

const TYPE_CONFIG: Record<
  NotificationTypeKey,
  {icon: string; color: string; bgColor: string}
> = {
  order_accepted: {icon: '✓', color: '#059669', bgColor: '#D1FAE5'},
  order_preparing: {icon: '♨', color: '#D97706', bgColor: '#FEF3C7'},
  order_ready: {icon: '↑', color: '#2563EB', bgColor: '#DBEAFE'},
  pickup_reminder: {icon: '!', color: '#7C3AED', bgColor: '#EDE9FE'},
  delay_alert: {icon: '⚠', color: '#DC2626', bgColor: '#FEE2E2'},
  order_cancelled: {icon: '✕', color: '#DC2626', bgColor: '#FEE2E2'},
  order_placed: {icon: '•', color: '#F59E0B', bgColor: '#FEF3C7'},
  promo: {icon: '%', color: '#0891B2', bgColor: '#CFFAFE'},
  system: {icon: 'i', color: '#6B7280', bgColor: '#F3F4F6'},
};

export function NotificationCard(props: {
  item: NotificationItem;
  onPress: () => void;
}) {
  const {item, onPress} = props;
  const isRead = item.is_read;
  const config = TYPE_CONFIG[item.notification_type] ?? TYPE_CONFIG.system;
  const timeAgo = getTimeAgo(item.created_at);

  return (
    <Pressable
      onPress={onPress}
      style={({pressed}) => [styles.wrapper, pressed && styles.pressed]}>
      <View style={[styles.card, !isRead && styles.unreadCard]}>
        <View style={styles.row}>
          <View style={[styles.iconBadge, {backgroundColor: config.bgColor}]}>
            <Text style={[styles.iconText, {color: config.color}]}>
              {config.icon}
            </Text>
          </View>
          <View style={styles.content}>
            <View style={styles.titleRow}>
              <Text style={[styles.title, !isRead && styles.unreadTitle]}>
                {item.title}
              </Text>
              {!isRead && <View style={styles.unreadDot} />}
            </View>
            <Text style={styles.message} numberOfLines={2}>
              {item.message}
            </Text>
            <Text style={styles.meta}>
              {timeAgo}
              {item.reference_id != null
                ? ` · Order #${item.reference_id}`
                : ''}
            </Text>
          </View>
        </View>
      </View>
    </Pressable>
  );
}

function getTimeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

const styles = StyleSheet.create({
  wrapper: {
    width: '100%',
  },
  pressed: {
    opacity: 0.85,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 12,
    shadowColor: 'rgba(0,0,0,0.06)',
    shadowOpacity: 0.06,
    shadowOffset: {width: 0, height: 2},
    shadowRadius: 6,
    elevation: 2,
  },
  unreadCard: {
    backgroundColor: '#F0F9FF',
    borderLeftWidth: 3,
    borderLeftColor: '#3B82F6',
  },
  row: {
    flexDirection: 'row',
    gap: 12,
  },
  iconBadge: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconText: {
    fontSize: 16,
    fontWeight: '800',
  },
  content: {
    flex: 1,
    gap: 3,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#374151',
  },
  unreadTitle: {
    fontWeight: '800',
    color: '#111827',
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#3B82F6',
  },
  message: {
    fontSize: 13,
    color: '#6B7280',
    lineHeight: 18,
  },
  meta: {
    fontSize: 11,
    color: '#9CA3AF',
    marginTop: 2,
  },
});
