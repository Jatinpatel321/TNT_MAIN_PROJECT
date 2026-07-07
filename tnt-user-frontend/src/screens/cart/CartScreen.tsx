import React, { useEffect, useMemo, useState } from 'react';
import { Alert, FlatList, Image, Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import { useCart } from '../../context/CartContext';
import { formatMoneyPaise } from '../../utils/format';
import { MENU_IMAGES } from '../../assets/images';
import { getVendorMenu } from '../../services/vendorService';
import { toAbsoluteUrl } from '../../utils/url';
import type { MenuItem } from '../../types/models';

type Props = NativeStackScreenProps<RootStackParamList, 'Cart'>;

export function CartScreen({ navigation }: Props) {
  const { cart, updateQuantity, removeItem, clearCart } = useCart();

  const [menuMap, setMenuMap] = useState<Record<number, MenuItem>>({});

  const total = cart?.total_amount ?? 0;
  const vendorId = cart?.vendor_id ?? null;

  useEffect(() => {
    (async () => {
      try {
        if (!vendorId) {
          setMenuMap({});
          return;
        }
        const list = await getVendorMenu(vendorId);
        const map: Record<number, MenuItem> = {};
        list.forEach((mi) => {
          map[mi.id] = mi;
        });
        setMenuMap(map);
      } catch (e) {
        // Non-blocking: cart can still render without images.
        setMenuMap({});
      }
    })();
  }, [vendorId]);

  const itemCountLabel = useMemo(() => {
    const n = cart?.total_items ?? 0;
    if (n === 1) return '1 item';
    return `${n} items`;
  }, [cart?.total_items]);

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Cart</Text>
        <Text style={styles.sub}>Manage items and checkout.</Text>
      </View>

      <FlatList
        data={cart?.items ?? []}
        keyExtractor={(item) => String(item.menu_item_id)}
        renderItem={({ item }) => {
          const imageKey = item.name?.toLowerCase().trim() || '';
          const localImage = MENU_IMAGES[imageKey];
          const menuItem = menuMap[item.menu_item_id];
          const remoteUri = toAbsoluteUrl(menuItem?.image_url ?? null);
          const source = localImage ?? (remoteUri ? { uri: remoteUri } : null);
          return (
            <View style={styles.card}>
              <View style={styles.row}>
                <View style={styles.imageWrap}>
                  {source ? (
                    <Image source={source} style={styles.image} />
                  ) : (
                    <View style={styles.placeholder}>
                      <MaterialCommunityIcons name="food" size={24} color="#6C63FF" />
                    </View>
                  )}
                </View>
                <View style={styles.info}>
                  <Text style={styles.itemName} numberOfLines={1}>{item.name}</Text>
                  <Text style={styles.meta}>{formatMoneyPaise(item.price)}</Text>
                </View>

                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Remove ${item.name} from cart`}
                  onPress={() => removeItem(item.menu_item_id)}
                  style={({ pressed }) => [styles.removeBtn, pressed && styles.removeBtnPressed]}
                >
                  <MaterialCommunityIcons name="trash-can-outline" size={18} color="#6B7280" />
                </Pressable>
              </View>
              <View style={styles.qtyRow}>
                <GradientButton
                  label="-"
                  onPress={() => updateQuantity(item.menu_item_id, item.quantity - 1)}
                  style={styles.smallBtn}
                />
                <Text style={styles.qtyValue}>{item.quantity}</Text>
                <GradientButton
                  label="+"
                  onPress={() => updateQuantity(item.menu_item_id, item.quantity + 1)}
                  style={styles.smallBtn}
                />
              </View>
            </View>
          );
        }}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
        ListEmptyComponent={<Text style={styles.muted}>Cart is empty.</Text>}
      />

      <View style={styles.totalCard}>
        <Text style={styles.totalLabel}>Total</Text>
        <Text style={styles.totalValue}>{formatMoneyPaise(total)}</Text>
      </View>

      <View style={styles.actions}>
        <GradientButton label="Clear Cart" onPress={clearCart} />
        <GradientButton
          label={`Checkout (${itemCountLabel})`}
          onPress={() => {
            if (!vendorId) {
              Alert.alert('No vendor selected', 'Add items from a vendor first.');
              return;
            }
            navigation.navigate('Checkout', { vendorId });
          }}
          disabled={!vendorId}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingVertical: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
  },
  sub: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  list: {
    paddingVertical: 10,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: 'rgba(0,0,0,0.1)',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 3,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginRight: 10,
  },
  imageWrap: {
    width: 50,
    height: 50,
    borderRadius: 10,
    overflow: 'hidden',
    backgroundColor: '#F3F4F6',
    marginRight: 12,
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
  info: {
    flex: 1,
  },
  removeBtn: {
    width: 34,
    height: 34,
    borderRadius: 12,
    backgroundColor: '#F9FAFB',
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  removeBtnPressed: {
    opacity: 0.85,
  },
  itemName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  meta: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 2,
  },
  qtyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    padding: 4,
  },
  smallBtn: {
    width: 32,
    height: 32,
    borderRadius: 10,
    marginHorizontal: 0,
  },
  qtyValue: {
    fontSize: 16,
    fontWeight: '700',
    width: 30,
    textAlign: 'center',
  },
  muted: {
    textAlign: 'center',
    color: '#9CA3AF',
    marginTop: 40,
  },
  totalCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#E0E7FF',
    padding: 20,
    borderRadius: 16,
    marginTop: 10,
    marginBottom: 20,
  },
  totalLabel: {
    fontSize: 18,
    fontWeight: '700',
    color: '#3730A3',
  },
  totalValue: {
    fontSize: 22,
    fontWeight: '800',
    color: '#3730A3',
  },
  actions: {
    gap: 12,
    marginBottom: 20,
  },
});
