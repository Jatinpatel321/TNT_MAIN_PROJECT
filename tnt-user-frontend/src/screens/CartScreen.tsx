import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Alert, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../types/navigation';
import type { Cart } from '../types/models';
import { Screen } from '../components/Screen';
import { RoundedCard } from '../components/RoundedCard';
import { GradientButton } from '../components/GradientButton';
import { clearCart, getCart, removeCartItem } from '../services/cartService';
import { formatMoneyPaise } from '../utils/format';
import { toApiError } from '../services/apiClient';

type Props = NativeStackScreenProps<RootStackParamList, 'Cart'>;

export function CartScreen({ navigation }: Props) {
  const [loading, setLoading] = useState(true);
  const [cart, setCart] = useState<Cart | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const c = await getCart();
      setCart(c);
    } catch (e) {
      Alert.alert('Failed to load cart', toApiError(e).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const unsub = navigation.addListener('focus', load);
    return unsub;
  }, [navigation, load]);

  const onRemove = async (menuItemId: number) => {
    try {
      const c = await removeCartItem(menuItemId);
      setCart(c);
    } catch (e) {
      Alert.alert('Remove failed', toApiError(e).message);
    }
  };

  const onClear = async () => {
    try {
      await clearCart();
      await load();
    } catch (e) {
      Alert.alert('Clear failed', toApiError(e).message);
    }
  };

  const vendorId = cart?.vendor_id ?? null;

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text variant="headlineSmall" style={styles.title}>Cart</Text>
        <Text style={styles.sub}>Single-vendor cart (backend enforced).</Text>
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator /></View>
      ) : !cart || cart.items.length === 0 ? (
        <Text style={styles.empty}>Your cart is empty.</Text>
      ) : (
        <>
          {cart.items.map((it) => (
            <RoundedCard key={it.menu_item_id}>
              <Text variant="titleMedium" style={styles.name}>{it.name}</Text>
              <Text style={styles.meta}>Qty: {it.quantity} • {formatMoneyPaise(it.price)}</Text>
              <View style={styles.row}>
                <Text style={styles.lineTotal}>Line: {formatMoneyPaise(it.price * it.quantity)}</Text>
                <GradientButton label="Remove" onPress={() => onRemove(it.menu_item_id)} style={styles.smallBtn} />
              </View>
            </RoundedCard>
          ))}

          <RoundedCard>
            <Text style={styles.total}>Items: {cart.total_items}</Text>
            <Text style={styles.total}>Total: {formatMoneyPaise(cart.total_amount)}</Text>
          </RoundedCard>

          <View style={styles.actions}>
            <GradientButton label="Clear Cart" onPress={onClear} />
            <GradientButton
              label="Choose Slot"
              onPress={() => {
                if (!vendorId) return;
                navigation.navigate('SlotSelection', { vendorId });
              }}
              disabled={!vendorId}
            />
          </View>
        </>
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
  center: {
    paddingVertical: 24,
    alignItems: 'center',
  },
  empty: {
    opacity: 0.7,
    paddingTop: 12,
  },
  name: {
    fontWeight: '800',
  },
  meta: {
    opacity: 0.7,
    marginTop: 4,
  },
  row: {
    marginTop: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  lineTotal: {
    fontWeight: '700',
  },
  smallBtn: {
    minWidth: 120,
  },
  total: {
    fontWeight: '800',
    marginVertical: 2,
  },
  actions: {
    gap: 10,
    paddingVertical: 14,
  },
});
