import React, {useCallback, useEffect, useState} from 'react';
import {ActivityIndicator, Pressable, StyleSheet, View} from 'react-native';
import {Text} from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import {NativeStackScreenProps} from '@react-navigation/native-stack';

import type {RootStackParamList} from '../../types/navigation';
import type {Order} from '../../types/models';
import {Screen} from '../../components/Screen';
import {
  getMyOrders,
  getPickupStatus,
  getOrderTimeline,
  ORDER_STATUS_LABELS,
  type PickupStatus,
} from '../../services/orderService';
import {toApiError} from '../../services/apiClient';
import {useAppTheme} from '../../theme/ThemeContext';
import {formatCurrency} from '../../utils/format';

type Props = NativeStackScreenProps<RootStackParamList, 'Receipt'>;

function fmtDateTime(iso?: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function ReceiptScreen({route, navigation}: Props) {
  const {orderId} = route.params;
  const {colors} = useAppTheme();

  const [order, setOrder] = useState<Order | null>(null);
  const [pickup, setPickup] = useState<PickupStatus | null>(null);
  const [pickedAt, setPickedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [orders, status] = await Promise.all([
        getMyOrders().catch(() => [] as Order[]),
        getPickupStatus(orderId).catch(() => null),
      ]);
      setOrder(orders.find(o => o.id === orderId) ?? null);
      setPickup(status);

      let confirmedAt = status?.pickup_confirmed_at ?? null;
      if (!confirmedAt) {
        // Fall back to the timeline's picked/completed transition.
        try {
          const tl = await getOrderTimeline(orderId);
          const pickedEntry = [...tl]
            .reverse()
            .find(t => ['picked', 'completed'].includes((t.status || '').toLowerCase()));
          confirmedAt = pickedEntry?.changed_at ?? null;
        } catch {
          /* ignore */
        }
      }
      setPickedAt(confirmedAt);
    } catch (e) {
      console.warn('[Receipt] load failed', toApiError(e).message);
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    load();
  }, [load]);

  const items = order?.items ?? [];
  const total = pickup?.total_amount ?? order?.total_amount ?? 0;
  const statusKey = (pickup?.status ?? order?.status ?? '').toLowerCase();
  const isPicked = statusKey === 'picked' || statusKey === 'completed';

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
          <MaterialCommunityIcons name="arrow-left" size={24} color={colors.text} />
        </Pressable>
        <Text style={[styles.title, {color: colors.text}]}>Receipt</Text>
        <View style={{width: 24}} />
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : (
        <View style={[styles.receipt, {backgroundColor: colors.surface, borderColor: colors.border}]}>
          {/* Brand header */}
          <View style={styles.brandRow}>
            <View style={[styles.brandIcon, {backgroundColor: colors.primarySoft}]}>
              <MaterialCommunityIcons name="silverware-fork-knife" size={22} color={colors.primary} />
            </View>
            <View>
              <Text style={[styles.brand, {color: colors.text}]}>Tap N Take</Text>
              <Text style={[styles.brandSub, {color: colors.muted}]}>Digital Pickup Receipt</Text>
            </View>
            <View
              style={[
                styles.statusPill,
                {backgroundColor: isPicked ? colors.successSoft : colors.warningSoft},
              ]}
            >
              <Text style={[styles.statusPillText, {color: isPicked ? colors.success : colors.warning}]}>
                {ORDER_STATUS_LABELS[statusKey] ?? pickup?.status ?? 'Order'}
              </Text>
            </View>
          </View>

          <View style={[styles.divider, {borderColor: colors.border}]} />

          {/* Meta */}
          <MetaRow label="Order Number" value={`#${orderId}`} colors={colors} />
          <MetaRow label="Vendor" value={pickup?.vendor_name ?? order?.vendor_name ?? '—'} colors={colors} />
          {pickup?.vendor_location ? (
            <MetaRow label="Location" value={pickup.vendor_location} colors={colors} />
          ) : null}
          <MetaRow label="Placed" value={fmtDateTime(order?.created_at) ?? '—'} colors={colors} />
          {pickedAt ? <MetaRow label="Picked Up" value={fmtDateTime(pickedAt) ?? '—'} colors={colors} /> : null}

          <View style={[styles.divider, {borderColor: colors.border}]} />

          {/* Items */}
          {items.length > 0 ? (
            <>
              <Text style={[styles.sectionLabel, {color: colors.muted}]}>ITEMS</Text>
              {items.map((it, idx) => (
                <View key={`${it.name}-${idx}`} style={styles.itemRow}>
                  <Text style={[styles.itemQty, {color: colors.muted}]}>{it.quantity}×</Text>
                  <Text style={[styles.itemName, {color: colors.text}]} numberOfLines={1}>
                    {it.name}
                  </Text>
                  <Text style={[styles.itemPrice, {color: colors.text}]}>
                    {formatCurrency(Number(it.price_at_time) * it.quantity, {inputType: 'rupees'})}
                  </Text>
                </View>
              ))}
              <View style={[styles.divider, {borderColor: colors.border}]} />
            </>
          ) : null}

          {/* Total */}
          <View style={styles.totalRow}>
            <Text style={[styles.totalLabel, {color: colors.text}]}>Total Paid</Text>
            <Text style={[styles.totalValue, {color: colors.primary}]}>
              {formatCurrency(total, {inputType: 'rupees'})}
            </Text>
          </View>

          {/* Footer */}
          <View style={[styles.footer, {borderColor: colors.border}]}>
            <MaterialCommunityIcons
              name={isPicked ? 'check-decagram' : 'information-outline'}
              size={16}
              color={isPicked ? colors.success : colors.muted}
            />
            <Text style={[styles.footerText, {color: colors.muted}]}>
              {isPicked
                ? 'Collected and verified via signed QR at the counter.'
                : 'This order has not been picked up yet.'}
            </Text>
          </View>
        </View>
      )}
    </Screen>
  );
}

function MetaRow({label, value, colors}: {
  label: string;
  value: string;
  colors: ReturnType<typeof useAppTheme>['colors'];
}) {
  return (
    <View style={styles.metaRow}>
      <Text style={[styles.metaLabel, {color: colors.muted}]}>{label}</Text>
      <Text style={[styles.metaValue, {color: colors.text}]} numberOfLines={1}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {fontSize: 18, fontWeight: '800'},
  center: {paddingVertical: 40, alignItems: 'center'},
  receipt: {
    marginTop: 10,
    borderRadius: 20,
    padding: 20,
    borderWidth: StyleSheet.hairlineWidth,
    shadowColor: 'rgba(0,0,0,0.10)',
    shadowOpacity: 0.1,
    shadowOffset: {width: 0, height: 4},
    shadowRadius: 12,
    elevation: 3,
  },
  brandRow: {flexDirection: 'row', alignItems: 'center', gap: 12},
  brandIcon: {
    width: 42,
    height: 42,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  brand: {fontSize: 16, fontWeight: '900'},
  brandSub: {fontSize: 12, fontWeight: '600'},
  statusPill: {marginLeft: 'auto', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999},
  statusPillText: {fontSize: 11, fontWeight: '800'},
  divider: {borderBottomWidth: StyleSheet.hairlineWidth, marginVertical: 14},
  metaRow: {flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4, gap: 12},
  metaLabel: {fontSize: 13, fontWeight: '600'},
  metaValue: {fontSize: 13, fontWeight: '700', flexShrink: 1, textAlign: 'right'},
  sectionLabel: {fontSize: 11, fontWeight: '800', letterSpacing: 0.5, marginBottom: 8},
  itemRow: {flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 5},
  itemQty: {fontSize: 13, fontWeight: '700', width: 28},
  itemName: {flex: 1, fontSize: 14, fontWeight: '600'},
  itemPrice: {fontSize: 14, fontWeight: '700'},
  totalRow: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'},
  totalLabel: {fontSize: 16, fontWeight: '800'},
  totalValue: {fontSize: 20, fontWeight: '900'},
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 16,
    paddingTop: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  footerText: {flex: 1, fontSize: 12, lineHeight: 17},
});
