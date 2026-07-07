import React, { useEffect, useMemo, useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import QRCode from 'react-native-qrcode-svg';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../types/navigation';
import type { Vendor } from '../../types/models';
import { Screen } from '../../components/Screen';
import { RoundedCard } from '../../components/RoundedCard';
import { getMyOrders, generateOrderQr } from '../../services/orderService';
import { getVendors } from '../../services/vendorService';
import { getSlots, type Slot } from '../../services/slotService';
import { toApiError } from '../../services/apiClient';

 type Props = NativeStackScreenProps<RootStackParamList, 'QR'>;

export function QRScreen({ route, navigation }: Props) {
  const { qrCode: initialQr, orderId } = route.params;

  const [qrValue, setQrValue] = useState(initialQr ?? '');
  const [vendorMap, setVendorMap] = useState<Record<number, Vendor>>({});
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(true);

  const [orderVendorId, setOrderVendorId] = useState<number | null>(null);
  const [orderSlotId, setOrderSlotId] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        // QR refresh if not passed in
        if (!initialQr) {
          try {
            const res = await generateOrderQr(orderId);
            setQrValue(res.qr_code);
          } catch (e) {
            Alert.alert('Unable to generate QR', toApiError(e).message);
          }
        }

        const [orders, slotsRes, food, stationery] = await Promise.all([
          getMyOrders(),
          getSlots(),
          getVendors('food'),
          getVendors('stationery'),
        ]);

        const ord = orders.find((o) => o.id === orderId);
        setOrderVendorId(ord?.vendor_id ?? null);
        setOrderSlotId(ord?.slot_id ?? null);
        setSlots(slotsRes.slots ?? slotsRes);
        const map: Record<number, Vendor> = {};
        [...food, ...stationery].forEach((v) => {
          map[v.id] = v;
        });
        setVendorMap(map);
      } catch (e) {
        Alert.alert('Unable to load order', toApiError(e).message);
      } finally {
        setLoading(false);
      }
    })();
  }, [orderId, initialQr]);

  const vendorName = useMemo(() => {
    if (orderVendorId && vendorMap[orderVendorId]) return vendorMap[orderVendorId].name ?? `Vendor #${orderVendorId}`;
    if (orderVendorId) return `Vendor #${orderVendorId}`;
    return 'Vendor';
  }, [orderVendorId, vendorMap]);

  const slotWindow = useMemo(() => {
    if (!orderSlotId) return null;
    const slot = slots.find((s) => s.id === orderSlotId);
    if (!slot) return null;
    const start = new Date(slot.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const end = new Date(slot.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return `${start} – ${end}`;
  }, [orderSlotId, slots]);

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Pickup QR Code</Text>
        <Text style={styles.sub} onPress={() => navigation.goBack()}>Back</Text>
      </View>

      <RoundedCard style={styles.card}>
        {qrValue ? (
          <View style={styles.qrWrap}>
            <QRCode
              value={JSON.stringify({ order_id: orderId, token: qrValue })}
              size={220}
            />
          </View>
        ) : (
          <Text style={styles.errorText}>Unable to generate QR</Text>
        )}

        <View style={styles.info}>
          <Text style={styles.label}>Order ID</Text>
          <Text style={styles.value}>#{orderId}</Text>
          <Text style={styles.label}>Vendor</Text>
          <Text style={styles.value}>{vendorName}</Text>
          {slotWindow ? (
            <>
              <Text style={styles.label}>Selected Slot</Text>
              <Text style={styles.value}>{slotWindow}</Text>
            </>
          ) : null}
        </View>

        <Text style={styles.instructions}>Show this QR code at the counter to collect your order.</Text>
      </RoundedCard>
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
  title: {
    fontSize: 18,
    fontWeight: '800',
  },
  sub: {
    fontSize: 14,
    color: '#6C63FF',
  },
  card: {
    marginTop: 14,
    padding: 20,
  },
  qrWrap: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  info: {
    marginTop: 16,
    gap: 4,
  },
  label: {
    fontSize: 13,
    color: '#6B7280',
  },
  value: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 6,
  },
  instructions: {
    marginTop: 12,
    fontSize: 14,
    color: '#4B5563',
  },
  errorText: {
    color: '#EF4444',
    textAlign: 'center',
  },
});
