import React from 'react';
import { Image, Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import type { Vendor } from '../types/models';
import { VENDOR_IMAGES } from '../assets/images';
import { toAbsoluteUrl } from '../utils/url';

export function VendorCard(props: { vendor: Vendor; onPress: () => void }) {
  const { vendor } = props;
  const slug = vendor.name?.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || '';
  const localImage = VENDOR_IMAGES[slug];
  const remoteUri = toAbsoluteUrl(vendor.logo_url);
  const fallbackUri = vendor.vendor_type === 'stationery'
    ? 'https://source.unsplash.com/600x400/?printing'
    : 'https://source.unsplash.com/600x400/?restaurant';
  const source = localImage ?? (remoteUri ? { uri: remoteUri } : { uri: fallbackUri });

  const rating = vendor.rating ?? null;
  const category = vendor.category ?? vendor.vendor_type?.toUpperCase() ?? 'FOOD';
  const location = vendor.location ?? null;

  return (
    <Pressable style={styles.card} onPress={props.onPress}>
      <View style={styles.imageWrap}>
        {source ? (
          <Image
            source={source}
            defaultSource={localImage ?? undefined}
            style={styles.image}
            resizeMode="cover"
          />
        ) : (
          <View style={styles.placeholder}>
            <Text style={styles.placeholderText}>{vendor.name?.charAt(0)?.toUpperCase() ?? 'V'}</Text>
          </View>
        )}
        {/* Rating badge */}
        {rating !== null && (
          <View style={styles.ratingBadge}>
            <Text style={styles.ratingText}>⭐ {rating.toFixed(1)}</Text>
          </View>
        )}
      </View>

      <Text style={styles.name} numberOfLines={1}>{vendor.name ?? `Vendor #${vendor.id}`}</Text>

      {/* Category chip */}
      <View style={styles.chipRow}>
        <View style={styles.chip}>
          <Text style={styles.chipText}>{category}</Text>
        </View>
        {vendor.express_pickup_eligible && (
          <View style={[styles.chip, styles.chipExpress]}>
            <Text style={[styles.chipText, styles.chipTextExpress]}>⚡ Express</Text>
          </View>
        )}
      </View>

      {location && (
        <Text style={styles.location} numberOfLines={1}>📍 {location}</Text>
      )}

      <Text style={styles.meta} numberOfLines={1}>Load: {vendor.live_load_label ?? '—'}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    width: '48%',
    minHeight: 210,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 10,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 6,
    elevation: 3,
  },
  imageWrap: {
    height: 120,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#F5F7FB',
    marginBottom: 10,
  },
  image: {
    width: '100%',
    height: '100%',
    borderRadius: 12,
  },
  placeholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderText: {
    fontSize: 24,
    fontWeight: '800',
    color: '#6C63FF',
  },
  ratingBadge: {
    position: 'absolute',
    right: 8,
    bottom: 8,
    backgroundColor: '#333',
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 6,
  },
  ratingText: {
    fontSize: 11,
    color: '#FFFFFF',
    fontWeight: '700',
  },
  name: {
    fontSize: 15,
    fontWeight: '700',
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    marginTop: 6,
  },
  chip: {
    backgroundColor: '#EDE9FE',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  chipText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#6C63FF',
  },
  chipExpress: {
    backgroundColor: '#FEF3C7',
  },
  chipTextExpress: {
    color: '#D97706',
  },
  location: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
  },
  meta: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 4,
  },
});
