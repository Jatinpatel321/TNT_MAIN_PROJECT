import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../types/navigation';
import type { MenuItem } from '../types/models';
import { Screen } from '../components/Screen';
import { RoundedCard } from '../components/RoundedCard';
import { GradientButton } from '../components/GradientButton';
import { addCartItem } from '../services/cartService';
import { getVendorMenu } from '../services/vendorService';
import { formatMoneyPaise } from '../utils/format';
import { toApiError } from '../services/apiClient';

type Props = NativeStackScreenProps<RootStackParamList, 'Menu'>;

export function MenuScreen({ route, navigation }: Props) {
  const { vendorId, vendorName } = route.params;

  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [addingId, setAddingId] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const list = await getVendorMenu(vendorId);
        setItems(list);
      } catch (e) {
        Alert.alert('Failed to load menu', toApiError(e).message);
      } finally {
        setLoading(false);
      }
    })();
  }, [vendorId]);

  const onAdd = async (item: MenuItem) => {
    try {
      setAddingId(item.id);
      await addCartItem(item.id, 1);
    } catch (e) {
      Alert.alert('Add to cart failed', toApiError(e).message);
    } finally {
      setAddingId(null);
    }
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text variant="headlineSmall" style={styles.title}>{vendorName ?? `Vendor #${vendorId}`}</Text>
        <Text style={styles.sub}>Tap to add items to your cart.</Text>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator />
        </View>
      ) : items.length === 0 ? (
        <Text style={styles.empty}>No menu items available.</Text>
      ) : (
        items.map((it) => (
          <RoundedCard key={it.id}>
            <Text variant="titleMedium" style={styles.name}>{it.name}</Text>
            {it.description ? <Text style={styles.desc}>{it.description}</Text> : null}
            <View style={styles.row}>
              <Text style={styles.price}>{formatMoneyPaise(it.price)}</Text>
              <GradientButton
                label={addingId === it.id ? 'Adding…' : 'Add'}
                onPress={() => onAdd(it)}
                disabled={addingId === it.id}
                style={styles.addBtn}
              />
            </View>
          </RoundedCard>
        ))
      )}

      <View style={styles.bottom}>
        <GradientButton label="Go to Cart" onPress={() => navigation.navigate('Cart')} />
      </View>
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
  desc: {
    opacity: 0.75,
    marginTop: 4,
  },
  row: {
    marginTop: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  price: {
    fontWeight: '800',
  },
  addBtn: {
    minWidth: 110,
  },
  bottom: {
    paddingVertical: 14,
  },
});
