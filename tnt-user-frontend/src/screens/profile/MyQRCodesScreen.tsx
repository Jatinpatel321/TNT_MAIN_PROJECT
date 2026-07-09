import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../types/navigation';
import type { Order, Vendor } from '../../types/models';
import { Screen } from '../../components/Screen';
import { generateOrderQr, getMyOrders } from '../../services/orderService';
import { getVendors } from '../../services/vendorService';
import { toApiError } from '../../services/apiClient';
import { useAppTheme } from '../../theme/ThemeContext';
import { EmptyState, FadeInSection, SectionCard, SkeletonBlock } from './profileUi';

type Props = NativeStackScreenProps<RootStackParamList, 'MyQRCodes'>;

const PICKUP_READY_STATUSES = new Set(['ready', 'ready_for_pickup']);

export function MyQRCodesScreen({ navigation }: Props) {
  const { colors } = useAppTheme();
  const [orders, setOrders] = useState<Order[]>([]);
  const [vendors, setVendors] = useState<Record<number, Vendor>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [openingId, setOpeningId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const [myOrders, food, stationery] = await Promise.all([
        getMyOrders(),
        getVendors('food').catch(() => [] as Vendor[]),
        getVendors('stationery').catch(() => [] as Vendor[]),
      ]);
      setOrders(myOrders.filter((o) => PICKUP_READY_STATUSES.has((o.status || '').toLowerCase())));
      const map: Record<number, Vendor> = {};
      [...food, ...stationery].forEach((v) => {
        map[v.id] = v;
      });
      setVendors(map);
    } catch (e) {
      Alert.alert('Failed to load QR codes', toApiError(e).message);
    }
  }, []);

  useEffect(() => {
    (async () => {
      await load();
      setLoading(false);
    })();
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const openQr = async (order: Order) => {
    try {
      setOpeningId(order.id);
      const qrCode = order.qr_code ?? (await generateOrderQr(order.id)).qr_code;
      navigation.navigate('QR', { qrCode, orderId: order.id });
    } catch (e) {
      Alert.alert('QR unavailable', toApiError(e).message);
    } finally {
      setOpeningId(null);
    }
  };

  return (
    <Screen scroll refreshing={refreshing} onRefresh={onRefresh}>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
          <MaterialCommunityIcons name="arrow-left" size={24} color={colors.text} />
        </Pressable>
        <Text style={[styles.title, { color: colors.text }]}>My QR Codes</Text>
        <View style={{ width: 24 }} />
      </View>

      <Text style={[styles.subtitle, { color: colors.muted }]}>
        Show these codes at the stall to collect orders that are ready.
      </Text>

      {loading ? (
        <View style={{ gap: 12, marginTop: 14 }}>
          <SkeletonBlock width={'100%' as const} height={84} radius={16} />
          <SkeletonBlock width={'100%' as const} height={84} radius={16} />
        </View>
      ) : orders.length === 0 ? (
        <SectionCard style={{ marginTop: 14 }}>
          <EmptyState
            icon="qrcode"
            title="No active pickup codes"
            subtitle="When an order is marked ready, its pickup QR appears here."
          />
        </SectionCard>
      ) : (
        <View style={{ gap: 12, marginTop: 14 }}>
          {orders.map((order, idx) => (
            <FadeInSection key={order.id} delay={idx * 60}>
              <Pressable onPress={() => openQr(order)} disabled={openingId === order.id}>
                <SectionCard>
                  <View style={styles.row}>
                    <View style={[styles.qrIcon, { backgroundColor: colors.primarySoft }]}>
                      <MaterialCommunityIcons
                        name={openingId === order.id ? 'timer-sand' : 'qrcode'}
                        size={26}
                        color={colors.primary}
                      />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.orderTitle, { color: colors.text }]}>
                        Order #{order.id}
                      </Text>
                      <Text style={[styles.orderMeta, { color: colors.muted }]}>
                        {vendors[order.vendor_id]?.name ?? `Vendor #${order.vendor_id}`}
                      </Text>
                    </View>
                    <View style={[styles.readyBadge, { backgroundColor: colors.successSoft }]}>
                      <Text style={[styles.readyBadgeText, { color: colors.success }]}>READY</Text>
                    </View>
                  </View>
                </SectionCard>
              </Pressable>
            </FadeInSection>
          ))}
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
  },
  subtitle: {
    fontSize: 13,
    lineHeight: 18,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  qrIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  orderTitle: {
    fontSize: 15,
    fontWeight: '800',
  },
  orderMeta: {
    fontSize: 12,
    marginTop: 1,
  },
  readyBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
  },
  readyBadgeText: {
    fontSize: 11,
    fontWeight: '800',
  },
});
