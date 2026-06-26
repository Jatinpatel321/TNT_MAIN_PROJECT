import React, {useEffect, useMemo, useState} from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import {Text} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';

import type {RootStackParamList} from '../../types/navigation';
import type {Order, Vendor} from '../../types/models';
import {Screen} from '../../components/Screen';
import {
  getMyOrders,
  isActiveOrder,
  reorderOrder,
} from '../../services/orderService';
import {toApiError} from '../../services/apiClient';
import {getVendors} from '../../services/vendorService';
import {OrderHistoryCard} from '../../components/OrderHistoryCard';

type Nav = NativeStackNavigationProp<RootStackParamList>;

type FilterTab = 'active' | 'past';

export function OrdersScreen() {
  const navigation = useNavigation<Nav>();
  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState<Order[]>([]);
  const [vendorMap, setVendorMap] = useState<Record<number, Vendor>>({});
  const [tab, setTab] = useState<FilterTab>('active');

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const [list, food, stationery] = await Promise.all([
          getMyOrders(),
          getVendors('food'),
          getVendors('stationery'),
        ]);
        setOrders(list);
        const map: Record<number, Vendor> = {};
        [...food, ...stationery].forEach(v => {
          map[v.id] = v;
        });
        setVendorMap(map);
      } catch (e) {
        Alert.alert('Failed to load orders', toApiError(e).message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = useMemo(() => {
    const sorted = [...orders].sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    return sorted.filter(o => {
      const active = isActiveOrder(o.status);
      return tab === 'active' ? active : !active;
    });
  }, [orders, tab]);

  const activeCount = useMemo(
    () => orders.filter(o => isActiveOrder(o.status)).length,
    [orders],
  );
  const pastCount = useMemo(
    () => orders.filter(o => !isActiveOrder(o.status)).length,
    [orders],
  );

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text variant="headlineSmall" style={styles.title}>
          My Orders
        </Text>
        <Text style={styles.sub}>Track status and pickup QR.</Text>
      </View>

      <View style={styles.tabRow}>
        <Pressable
          style={[styles.tab, tab === 'active' && styles.tabActive]}
          onPress={() => setTab('active')}>
          <Text
            style={[styles.tabText, tab === 'active' && styles.tabTextActive]}>
            Active ({activeCount})
          </Text>
        </Pressable>
        <Pressable
          style={[styles.tab, tab === 'past' && styles.tabActive]}
          onPress={() => setTab('past')}>
          <Text
            style={[styles.tabText, tab === 'past' && styles.tabTextActive]}>
            Past ({pastCount})
          </Text>
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator />
        </View>
      ) : orders.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={styles.emptyTitle}>No orders yet</Text>
          <Text style={styles.emptySub}>
            Place your first order from a vendor!
          </Text>
        </View>
      ) : filtered.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>{tab === 'active' ? '✅' : '📦'}</Text>
          <Text style={styles.emptyTitle}>
            {tab === 'active' ? 'No active orders' : 'No past orders'}
          </Text>
          <Text style={styles.emptySub}>
            {tab === 'active'
              ? 'All your orders are completed!'
              : 'Your active orders will appear here when completed.'}
          </Text>
        </View>
      ) : (
        filtered.map(o => {
          const vendor = vendorMap[o.vendor_id];
          const vendorName =
            o.vendor_name ?? vendor?.name ?? `Vendor #${o.vendor_id}`;
          const totalRupees =
            typeof o.total_amount === 'number'
              ? o.total_amount < 100
                ? Number(o.total_amount)
                : Number(o.total_amount) / 100
              : null;
          return (
            <OrderHistoryCard
              key={o.id}
              order={o}
              vendorName={vendorName}
              vendorLogoUrl={vendor?.logo_url ?? null}
              totalAmount={totalRupees}
              onPress={() =>
                navigation.navigate('OrderTracking', {orderId: o.id})
              }
            />
          );
        })
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: 18,
    paddingBottom: 8,
  },
  title: {
    fontWeight: '900',
  },
  sub: {
    opacity: 0.7,
    marginTop: 4,
  },
  tabRow: {
    flexDirection: 'row',
    backgroundColor: '#F3F4F6',
    borderRadius: 12,
    padding: 4,
    marginBottom: 12,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 10,
  },
  tabActive: {
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: {width: 0, height: 1},
    shadowRadius: 2,
    elevation: 1,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
  },
  tabTextActive: {
    color: '#111827',
    fontWeight: '700',
  },
  center: {
    paddingVertical: 24,
    alignItems: 'center',
  },
  emptyContainer: {
    alignItems: 'center',
    paddingTop: 40,
    gap: 8,
  },
  emptyIcon: {
    fontSize: 48,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
  },
  emptySub: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
  },
});
