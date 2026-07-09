import React, { useMemo } from 'react';
import { Image, Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import type { Vendor } from '../types/models';
import { VENDOR_IMAGES } from '../assets/images';
import { toAbsoluteUrl } from '../utils/url';
import { useAppTheme } from '../theme/ThemeContext';
import type { AppPalette } from '../theme/theme';

export function VendorCard(props: {
  vendor: Vendor;
  onPress: () => void;
  isFavorite?: boolean;
  onToggleFavorite?: () => void;
}) {
  const { vendor, isFavorite, onToggleFavorite } = props;
  const { colors } = useAppTheme();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  const slug = vendor.name?.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || '';
  const localImage = VENDOR_IMAGES[slug];
  const remoteUri = toAbsoluteUrl(vendor.logo_url);
  const fallbackUri = vendor.vendor_type === 'stationery'
    ? 'https://images.unsplash.com/photo-1456735190827-d1262f71b8a3?auto=format&fit=crop&w=600&q=70'
    : 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=600&q=70';
  // Prefer the real remote photo; bundled assets are low-res placeholders kept
  // only as an offline fallback.
  const source = remoteUri ? { uri: remoteUri } : (localImage ?? { uri: fallbackUri });

  const rating = vendor.rating ?? null;
  const category = vendor.category ?? vendor.vendor_type?.toUpperCase() ?? 'FOOD';
  const location = vendor.location ?? null;

  return (
    <Pressable style={styles.card} onPress={props.onPress}>
      <View style={styles.imageWrap}>
        {source ? (
          <Image
            source={source}
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
        {onToggleFavorite && (
          <Pressable
            style={styles.favoriteBtn}
            onPress={(e) => {
              e.stopPropagation?.();
              onToggleFavorite();
            }}
            hitSlop={8}
          >
            <Text style={styles.favoriteIcon}>{isFavorite ? '❤️' : '🤍'}</Text>
          </Pressable>
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

const makeStyles = (colors: AppPalette) => StyleSheet.create({
  card: {
    width: '48%',
    minHeight: 210,
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 10,
    marginBottom: 16,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
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
    backgroundColor: colors.surfaceAlt,
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
    color: colors.primary,
  },
  ratingBadge: {
    position: 'absolute',
    right: 8,
    bottom: 8,
    backgroundColor: 'rgba(0,0,0,0.72)',
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 6,
  },
  ratingText: {
    fontSize: 11,
    color: '#FFFFFF',
    fontWeight: '700',
  },
  favoriteBtn: {
    position: 'absolute',
    left: 8,
    top: 8,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.85)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  favoriteIcon: {
    fontSize: 14,
  },
  name: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.text,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    marginTop: 6,
  },
  chip: {
    backgroundColor: colors.primarySoft,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  chipText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.primary,
  },
  chipExpress: {
    backgroundColor: colors.warningSoft,
  },
  chipTextExpress: {
    color: colors.warning,
  },
  location: {
    fontSize: 12,
    color: colors.muted,
    marginTop: 4,
  },
  meta: {
    fontSize: 12,
    color: colors.muted,
    marginTop: 4,
  },
});
