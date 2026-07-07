import React, { useEffect, useState } from 'react';
import { Alert, Image, ScrollView, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { MaterialCommunityIcons } from '@expo/vector-icons';

import type { RootStackParamList } from '../types/navigation';
import type { Vendor, Order } from '../types/models';
import { Screen } from '../components/Screen';
import { OfferBanner } from '../components/OfferBanner';
import { ShortcutCard } from '../components/ShortcutCard';
import { VendorCard } from '../components/VendorCard';
import { RecentOrderCard } from '../components/RecentOrderCard';
import { getVendors } from '../services/vendorService';
import { getMyOrders } from '../services/orderService';
import { toApiError } from '../services/apiClient';
import { LOGO } from '../assets';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const [popularVendors, setPopularVendors] = useState<Vendor[]>([]);
  const [vendorMap, setVendorMap] = useState<Record<number, string>>({});
  const [recentOrders, setRecentOrders] = useState<Order[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(false);

  useEffect(() => {
    (async () => {
      // Vendors (food for popularity) and map for names
      try {
        const [foodVendors, stationeryVendors] = await Promise.all([
          getVendors('food'),
          getVendors('stationery'),
        ]);
        setPopularVendors(foodVendors.slice(0, 6));
        const map: Record<number, string> = {};
        [...foodVendors, ...stationeryVendors].forEach((v) => {
          map[v.id] = v.name ?? `Vendor #${v.id}`;
        });
        setVendorMap(map);
      } catch (e) {
        Alert.alert('Vendors unavailable', toApiError(e).message);
      }

      // Recent orders
      try {
        setLoadingOrders(true);
        const orders = await getMyOrders();
        const sorted = [...orders].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setRecentOrders(sorted.slice(0, 5));
      } catch (e) {
        Alert.alert('Orders unavailable', toApiError(e).message);
      } finally {
        setLoadingOrders(false);
      }
    })();
  }, []);

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <View style={styles.brandRow}>
            <Image source={LOGO} style={styles.brandLogo} resizeMode="contain" />
            <View>
              <Text style={styles.brandTitle}>Tap N Take</Text>
              <Text style={styles.subtitle}>Schedule smarter. Pick up faster.</Text>
            </View>
          </View>
          <MaterialCommunityIcons
            name="bell-outline"
            size={26}
            color="#6C63FF"
            onPress={() => navigation.navigate('NotificationsTab' as any)}
          />
        </View>

        <View style={styles.sectionSpacing}>
          <OfferBanner />
        </View>

        <View style={styles.shortcutsRow}>
          <ShortcutCard
            title="Food Scheduling"
            subtitle="Order Food"
            icon="silverware-fork-knife"
            onPress={() => navigation.navigate('VendorList', { type: 'food' })}
          />
          <ShortcutCard
            title="Stationery Scheduling"
            subtitle="Print & Xerox"
            icon="file-document-outline"
            onPress={() => navigation.navigate('VendorList', { type: 'stationery' })}
          />
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Popular Vendors</Text>
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.horizontalList}>
          {popularVendors.map((v) => (
            <VendorCard key={v.id} vendor={v} onPress={() => navigation.navigate('Menu', { vendorId: v.id, vendorName: v.name })} />
          ))}
          {popularVendors.length === 0 && <Text style={styles.muted}>No vendors available.</Text>}
        </ScrollView>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Recent Orders</Text>
        </View>
        {loadingOrders ? (
          <Text style={styles.muted}>Loading…</Text>
        ) : recentOrders.length === 0 ? (
          <Text style={styles.muted}>No recent orders.</Text>
        ) : (
          recentOrders.map((o) => (
            <RecentOrderCard
              key={o.id}
              order={o}
              vendorName={vendorMap[o.vendor_id] ?? `Vendor #${o.vendor_id}`}
              onPress={() => navigation.navigate('OrderTracking', { orderId: o.id })}
            />
          ))
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: 20,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 10,
    paddingBottom: 10,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  brandLogo: {
    width: 32,
    height: 32,
  },
  brandTitle: {
    fontSize: 16,
    fontWeight: '800',
  },
  subtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  sectionSpacing: {
    marginTop: 20,
  },
  shortcutsRow: {
    marginTop: 20,
    flexDirection: 'row',
    gap: 10,
  },
  sectionHeader: {
    marginTop: 20,
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  horizontalList: {
    paddingBottom: 4,
  },
  muted: {
    fontSize: 14,
    color: '#6B7280',
  },
});
