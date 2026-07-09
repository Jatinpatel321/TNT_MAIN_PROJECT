import React from 'react';
import { Image, Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import type { MenuItem } from '../types/models';
import { MENU_IMAGES } from '../assets/images';
import { toAbsoluteUrl } from '../utils/url';
import { formatMoney } from '../utils/format';

export function MenuItemCard(props: {
  item: MenuItem;
  quantity: number;
  onIncrement: () => void;
  onDecrement: () => void;
  isFavorite?: boolean;
  onToggleFavorite?: () => void;
}) {
  const { item, quantity, onIncrement, onDecrement, isFavorite, onToggleFavorite } = props;
  const available = item.is_available !== false;
  const imageKey = item.name?.toLowerCase().trim() || '';
  const localImage = MENU_IMAGES[imageKey];
  const remoteUri = toAbsoluteUrl(item.image_url);
  const fallbackUri = 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=600&q=70';
  // Prefer the real remote photo; the bundled assets are low-res placeholders
  // and only serve as an offline fallback.
  const source = remoteUri ? { uri: remoteUri } : (localImage ?? { uri: fallbackUri });

  return (
    <Pressable style={styles.card}>
      <View style={styles.row}>
        <View style={styles.info}>
          <View style={styles.nameRow}>
            <Text style={styles.name} numberOfLines={1}>{item.name}</Text>
            {onToggleFavorite && (
              <Pressable onPress={onToggleFavorite} hitSlop={8}>
                <Text style={styles.favoriteIcon}>{isFavorite ? '❤️' : '🤍'}</Text>
              </Pressable>
            )}
          </View>
          {item.description ? <Text style={styles.desc} numberOfLines={2}>{item.description}</Text> : null}
          <Text style={styles.meta}>{formatMoney(item.price)} • Prep: {item.prep_time_minutes ?? 'Varies'} min</Text>
          {!available && <Text style={styles.unavailable}>Unavailable</Text>}
        </View>
        {source ? (
          <Image
            source={source}
            style={styles.image}
            resizeMode="cover"
          />
        ) : (
          <View style={styles.placeholder}>
            <MaterialCommunityIcons name="food" size={26} color="#6C63FF" />
          </View>
        )}
      </View>
      <View style={styles.actions}>
        <Pressable style={[styles.qtyBtn, !available && styles.disabledBtn]} disabled={!available} onPress={onDecrement}>
          <Text style={styles.qtyText}>-</Text>
        </Pressable>
        <Text style={styles.qtyValue}>{quantity}</Text>
        <Pressable style={[styles.qtyBtn, !available && styles.disabledBtn]} disabled={!available} onPress={onIncrement}>
          <Text style={styles.qtyText}>+</Text>
        </Pressable>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 16,
    marginBottom: 10,
    shadowColor: 'rgba(0,0,0,0.1)',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 4,
  },
  row: {
    flexDirection: 'row',
    gap: 12,
  },
  info: {
    flex: 1,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  name: {
    fontSize: 16,
    fontWeight: '700',
    flexShrink: 1,
  },
  favoriteIcon: {
    fontSize: 16,
  },
  desc: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  meta: {
    fontSize: 14,
    color: '#111827',
    marginTop: 6,
  },
  unavailable: {
    marginTop: 4,
    color: '#EF4444',
    fontWeight: '700',
  },
  image: {
    width: 90,
    height: 90,
    borderRadius: 12,
    backgroundColor: '#F5F7FB',
  },
  placeholder: {
    width: 90,
    height: 90,
    borderRadius: 12,
    backgroundColor: '#F5F7FB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 12,
    marginTop: 12,
  },
  qtyBtn: {
    width: 36,
    height: 36,
    borderRadius: 12,
    backgroundColor: '#F5F7FB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  disabledBtn: {
    opacity: 0.4,
  },
  qtyText: {
    fontSize: 18,
    fontWeight: '800',
  },
  qtyValue: {
    fontSize: 16,
    fontWeight: '700',
  },
});
