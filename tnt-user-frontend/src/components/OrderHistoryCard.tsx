import React, {useMemo} from 'react';
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
import {formatCurrency} from '../utils/format';
import {useAppTheme} from '../theme/ThemeContext';
import type {AppPalette} from '../theme/theme';

export function OrderHistoryCard(props: {
  order: Order;
  vendorName: string;
  vendorLogoUrl?: string | null;
  totalAmount?: number | null;
  onPress: () => void;
  onShowQr?: () => void;
}) {
  const {order, vendorName, vendorLogoUrl, totalAmount, onPress, onShowQr} = props;
  const {colors} = useAppTheme();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  const statusKey = (order.status || '').toLowerCase();
  const isReadyForPickup = statusKey === 'ready' || statusKey === 'ready_for_pickup';
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
              {formatCurrency(totalAmount, { inputType: 'rupees' })}
            </Text>
          ) : null}
        </View>

        {isReadyForPickup && onShowQr ? (
          <Pressable
            onPress={onShowQr}
            style={({pressed}) => [styles.pickupCta, pressed && {opacity: 0.85}]}>
            <Text style={styles.pickupCtaText}>📲  Show Pickup QR</Text>
          </Pressable>
        ) : null}
      </View>
    </Pressable>
  );
}

const makeStyles = (colors: AppPalette) => StyleSheet.create({
  wrap: {
    width: '100%',
  },
  pressed: {
    opacity: 0.9,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 18,
    padding: 16,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    shadowColor: 'rgba(0,0,0,0.08)',
    shadowOpacity: 0.08,
    shadowOffset: {width: 0, height: 3},
    shadowRadius: 8,
    elevation: 4,
    marginVertical: 4,
  },
  activeCard: {
    borderLeftWidth: 3,
    borderLeftColor: colors.accent,
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
    backgroundColor: colors.surfaceAlt,
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
    backgroundColor: colors.primarySoft,
  },
  placeholderText: {
    fontWeight: '700',
    color: colors.primary,
  },
  headerInfo: {
    flex: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.text,
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
    color: colors.danger,
    backgroundColor: colors.dangerSoft,
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
    borderTopColor: colors.border,
  },
  orderId: {
    fontSize: 13,
    color: colors.muted,
  },
  dateText: {
    fontSize: 12,
    color: colors.muted,
    marginTop: 2,
  },
  total: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.text,
  },
  pickupCta: {
    marginTop: 12,
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 11,
    alignItems: 'center',
  },
  pickupCtaText: {
    color: colors.onPrimary,
    fontSize: 14,
    fontWeight: '800',
  },
});
