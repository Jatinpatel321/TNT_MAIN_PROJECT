import React from 'react';
import {Image, Pressable, StyleSheet, View} from 'react-native';
import {Text} from 'react-native-paper';

import type {Order} from '../types/models';
import {
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
  isActiveOrder,
} from '../services/orderService';
import {VENDOR_IMAGES} from '../assets/images';
import {toAbsoluteUrl} from '../utils/url';

export function OrderHistoryCard(props: {
  order: Order;
  vendorName: string;
  vendorLogoUrl?: string | null;
  totalAmount?: number | null;
  onPress: () => void;
}) {
  const {order, vendorName, vendorLogoUrl, totalAmount, onPress} = props;
  const statusKey = (order.status || '').toLowerCase();
  const statusLabel = ORDER_STATUS_LABELS[statusKey] ?? order.status;
  const statusColor = ORDER_STATUS_COLORS[statusKey] ?? '#6B7280';
  const active = isActiveOrder(statusKey);
  const slug =
    vendorName
      ?.toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '') || '';
  const localImage = VENDOR_IMAGES[slug];
  const remoteUri = toAbsoluteUrl(vendorLogoUrl || null);
  const source = localImage ?? (remoteUri ? {uri: remoteUri} : null);

  const isDelayed = order.is_delayed ?? false;

  return (
    <Pressable
      onPress={onPress}
      style={({pressed}) => [styles.wrap, pressed && styles.pressed]}>
      <View style={[styles.card, active && styles.activeCard]}>
        <View style={styles.headerRow}>
          <View style={styles.logoWrap}>
            {source ? (
              <Image source={source} style={styles.image} />
            ) : (
              <View style={styles.placeholder}>
                <Text style={styles.placeholderText}>
                  {vendorName?.[0] || 'V'}
                </Text>
              </View>
            )}
          </View>
          <View style={styles.headerInfo}>
            <Text style={styles.title}>{vendorName}</Text>
            <View style={styles.statusRow}>
              <View
                style={[styles.statusDot, {backgroundColor: statusColor}]}
              />
              <Text style={[styles.statusText, {color: statusColor}]}>
                {statusLabel}
              </Text>
              {isDelayed && <Text style={styles.delayBadge}>Delayed</Text>}
            </View>
          </View>
        </View>
        <View style={styles.row}>
          <View>
            <Text style={styles.orderId}>Order #{order.id}</Text>
            <Text style={styles.dateText}>
              {new Date(order.created_at).toLocaleDateString()}
            </Text>
          </View>
          {typeof totalAmount === 'number' ? (
            <Text style={styles.total}>
              {totalAmount < 100
                ? `₹${Number(totalAmount).toFixed(2)}`
                : `₹${(Number(totalAmount) / 100).toFixed(2)}`}
            </Text>
          ) : null}
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: '100%',
  },
  pressed: {
    opacity: 0.9,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 16,
    shadowColor: 'rgba(0,0,0,0.08)',
    shadowOpacity: 0.08,
    shadowOffset: {width: 0, height: 3},
    shadowRadius: 8,
    elevation: 4,
    marginVertical: 4,
  },
  activeCard: {
    borderLeftWidth: 3,
    borderLeftColor: '#3B82F6',
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  logoWrap: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: '#F3F4F6',
    marginRight: 12,
    overflow: 'hidden',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  placeholder: {
    width: '100%',
    height: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderText: {
    fontWeight: '700',
    color: '#3730A3',
  },
  headerInfo: {
    flex: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: '800',
    color: '#111827',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 2,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusText: {
    fontSize: 13,
    fontWeight: '700',
  },
  delayBadge: {
    fontSize: 11,
    fontWeight: '700',
    color: '#EF4444',
    backgroundColor: '#FEF2F2',
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 8,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
  },
  orderId: {
    fontSize: 13,
    color: '#6B7280',
  },
  dateText: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 2,
  },
  total: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
  },
});
