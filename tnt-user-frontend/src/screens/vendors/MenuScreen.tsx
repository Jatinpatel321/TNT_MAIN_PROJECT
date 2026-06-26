import React, { useEffect, useMemo, useState } from 'react';
import { Alert, FlatList, Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import type { RootStackParamList } from '../../types/navigation';
import type { MenuItem } from '../../types/models';
import { Screen } from '../../components/Screen';
import { MenuItemCard } from '../../components/MenuItemCard';
import { getVendorMenu } from '../../services/vendorService';
import { toApiError } from '../../services/apiClient';
import { useCart } from '../../context/CartContext';
import { GradientButton } from '../../components/GradientButton';

type Props = NativeStackScreenProps<RootStackParamList, 'Menu'>;

export function MenuScreen({ route, navigation }: Props) {
  const { vendorId, vendorName } = route.params;
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(false);
  const { cart, updateQuantity, addItem } = useCart();

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const items = await getVendorMenu(vendorId);
        setMenu(items);
      } catch (e) {
        Alert.alert('Menu unavailable', toApiError(e).message);
      } finally {
        setLoading(false);
      }
    })();
  }, [vendorId]);

  const getQty = (menuItemId: number) => cart?.items.find((i) => i.menu_item_id === menuItemId)?.quantity ?? 0;

  const cartCount = cart?.total_items ?? 0;
  const canViewCart = cartCount > 0 && (cart?.vendor_id == null || cart.vendor_id === vendorId);
  const viewCartLabel = useMemo(() => {
    if (cartCount === 1) return 'View Cart (1 item)';
    return `View Cart (${cartCount} items)`;
  }, [cartCount]);

  return (
    <Screen>
      <View style={styles.headerRow}>
        <View style={styles.headerLeft}>
          <Text style={styles.title}>{vendorName ?? `Vendor #${vendorId}`}</Text>
          <Text style={styles.sub}>Menu</Text>
        </View>

        <Pressable
          accessibilityRole="button"
          onPress={() => navigation.navigate('Cart')}
          style={({ pressed }) => [styles.cartBtn, pressed && styles.pressed]}
        >
          <MaterialCommunityIcons name="cart-outline" size={22} color="#111827" />
          {cartCount > 0 ? (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{cartCount}</Text>
            </View>
          ) : null}
        </Pressable>
      </View>

      <FlatList
        data={menu}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <MenuItemCard
            item={item}
            quantity={getQty(item.id)}
            onIncrement={() => addItem(item.id, 1)}
            onDecrement={() => updateQuantity(item.id, getQty(item.id) - 1)}
          />
        )}
        contentContainerStyle={[styles.list, canViewCart && styles.listWithFooter]}
        ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
        ListEmptyComponent={!loading ? <Text style={styles.muted}>No items available.</Text> : null}
      />

      {canViewCart ? (
        <View style={styles.floatingWrap}>
          <GradientButton label={viewCartLabel} onPress={() => navigation.navigate('Cart')} />
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  headerRow: {
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  headerLeft: {
    flex: 1,
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
  listWithFooter: {
    paddingBottom: 90,
  },
  muted: {
    color: '#6B7280',
    textAlign: 'center',
    marginTop: 12,
  },
  cartBtn: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.85,
  },
  badge: {
    position: 'absolute',
    top: 6,
    right: 6,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    paddingHorizontal: 4,
    backgroundColor: '#6C63FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  floatingWrap: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 16,
  },
});
