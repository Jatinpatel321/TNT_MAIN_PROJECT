import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { getSmartReorder } from '../../services/recommendationService';
import type { SmartReorderItem as SmartReorderItemType } from '../../services/recommendationService';
import { formatMoneyPaise } from '../../utils/format';
import { useCart } from '../../context/CartContext';
import { toApiError } from '../../services/apiClient';

type Props = NativeStackScreenProps<RootStackParamList, 'SmartReorder'>;

export function SmartReorderScreen({ navigation }: Props) {
  const { cart, clearCart, addItem } = useCart();
  const [items, setItems] = useState<SmartReorderItemType[]>([]);
  const [bestTime, setBestTime] = useState('');
  const [bestSlotId, setBestSlotId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [reorderingId, setReorderingId] = useState<number | null>(null);

  // Populate the cart with the suggested item at its suggested quantity, then
  // jump straight to checkout. The cart is single-vendor, so if it already
  // holds items we confirm before replacing them.
  const reorderToCart = async (item: SmartReorderItemType) => {
    try {
      setReorderingId(item.item_id);
      await clearCart();
      await addItem(item.item_id, Math.max(1, item.suggested_quantity));
      navigation.navigate('Checkout', { vendorId: item.vendor_id });
    } catch (e) {
      Alert.alert('Reorder failed', toApiError(e).message);
    } finally {
      setReorderingId(null);
    }
  };

  const onReorderPress = (item: SmartReorderItemType) => {
    const hasItems = (cart?.total_items ?? 0) > 0;
    const differentVendor = cart?.vendor_id != null && cart.vendor_id !== item.vendor_id;
    if (hasItems && differentVendor) {
      Alert.alert(
        'Replace current cart?',
        `Your cart has items from another vendor. Reordering ${item.item_name} will start a new order.`,
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Reorder', style: 'destructive', onPress: () => reorderToCart(item) },
        ],
      );
    } else {
      reorderToCart(item);
    }
  };

  const loadData = async () => {
    try {
      const data = await getSmartReorder();
      setItems(data.items);
      setBestTime(data.best_reorder_time);
      setBestSlotId(data.best_reorder_slot_id);
    } catch {
      // silent
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  if (loading) {
    return (
      <Screen>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#3B82F6" />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Pressable onPress={() => navigation.goBack()} style={styles.backBtn}>
            <MaterialCommunityIcons name="arrow-left" size={22} color="#111827" />
          </Pressable>
          <Text style={styles.title}>Smart Reorder</Text>
        </View>

        {bestTime && (
          <View style={styles.timeCard}>
            <View style={styles.timeIconWrap}>
              <MaterialCommunityIcons name="clock-outline" size={22} color="#3B82F6" />
            </View>
            <View style={styles.timeContent}>
              <Text style={styles.timeLabel}>Best Time to Reorder</Text>
              <Text style={styles.timeValue}>{bestTime}</Text>
            </View>
          </View>
        )}

        {items.length === 0 ? (
          <View style={styles.emptyState}>
            <MaterialCommunityIcons name="basket-outline" size={48} color="#D1D5DB" />
            <Text style={styles.emptyTitle}>No reorder suggestions yet</Text>
            <Text style={styles.emptyText}>
              Place a few orders and we'll suggest your favorites here!
            </Text>
          </View>
        ) : (
          items.map((item) => (
            <View key={item.item_id} style={styles.itemCard}>
              <Pressable
                style={styles.itemMain}
                onPress={() =>
                  navigation.navigate('Menu', {
                    vendorId: item.vendor_id,
                    vendorName: item.vendor_name,
                  })
                }
              >
                <View style={styles.itemLeft}>
                  <View style={styles.itemCountBadge}>
                    <Text style={styles.itemCountText}>{item.order_count}x</Text>
                  </View>
                </View>
                <View style={styles.itemContent}>
                  <Text style={styles.itemName}>{item.item_name}</Text>
                  <Text style={styles.itemVendor}>{item.vendor_name}</Text>
                  <Text style={styles.itemLast}>
                    Last ordered {new Date(item.last_ordered_at).toLocaleDateString()}
                  </Text>
                  {item.suggested_slot_time && (
                    <View style={styles.slotHint}>
                      <MaterialCommunityIcons name="clock-fast" size={14} color="#3B82F6" />
                      <Text style={styles.slotHintText}>
                        Suggested: {item.suggested_slot_time}
                      </Text>
                    </View>
                  )}
                </View>
                <View style={styles.itemRight}>
                  <Text style={styles.itemPrice}>
                    {formatMoneyPaise(item.price_paise)}
                  </Text>
                  <Text style={styles.itemQty}>Qty: {item.suggested_quantity}</Text>
                </View>
              </Pressable>
              <Pressable
                style={styles.reorderBtn}
                onPress={() => onReorderPress(item)}
                disabled={reorderingId === item.item_id}
              >
                {reorderingId === item.item_id ? (
                  <ActivityIndicator size="small" color="#FFFFFF" />
                ) : (
                  <>
                    <MaterialCommunityIcons name="cart-plus" size={16} color="#FFFFFF" />
                    <Text style={styles.reorderBtnText}>Reorder &amp; Checkout</Text>
                  </>
                )}
              </Pressable>
            </View>
          ))
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: 32,
    gap: 12,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 8,
  },
  backBtn: {
    padding: 4,
  },
  title: {
    fontSize: 22,
    fontWeight: '900',
    color: '#111827',
  },
  timeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#EFF6FF',
    borderRadius: 16,
    padding: 16,
    gap: 12,
  },
  timeIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: '#DBEAFE',
    alignItems: 'center',
    justifyContent: 'center',
  },
  timeContent: {
    flex: 1,
    gap: 2,
  },
  timeLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6B7280',
  },
  timeValue: {
    fontSize: 18,
    fontWeight: '800',
    color: '#1D4ED8',
  },
  emptyState: {
    backgroundColor: '#F9FAFB',
    borderRadius: 20,
    padding: 32,
    alignItems: 'center',
    gap: 8,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#374151',
    marginTop: 8,
  },
  emptyText: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
  },
  itemCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 14,
    gap: 12,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
    elevation: 2,
  },
  itemMain: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  reorderBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#6C63FF',
    borderRadius: 12,
    paddingVertical: 10,
  },
  reorderBtnText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  itemLeft: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: '#D1FAE5',
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemCountBadge: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemCountText: {
    fontSize: 14,
    fontWeight: '800',
    color: '#059669',
  },
  itemContent: {
    flex: 1,
    gap: 2,
  },
  itemName: {
    fontSize: 15,
    fontWeight: '700',
    color: '#111827',
  },
  itemVendor: {
    fontSize: 12,
    color: '#6B7280',
  },
  itemLast: {
    fontSize: 11,
    color: '#9CA3AF',
  },
  slotHint: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 2,
  },
  slotHintText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#3B82F6',
  },
  itemRight: {
    alignItems: 'flex-end',
    gap: 2,
  },
  itemPrice: {
    fontSize: 15,
    fontWeight: '800',
    color: '#111827',
  },
  itemQty: {
    fontSize: 11,
    color: '#9CA3AF',
  },
});
