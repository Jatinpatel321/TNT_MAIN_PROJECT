import React, { useEffect, useState } from 'react';
import { Alert, Image, ScrollView, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../types/navigation';
import type { Vendor, VendorSlot } from '../../types/models';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import { getVendors, getVendorSlots } from '../../services/vendorService';
import { toApiError } from '../../services/apiClient';
import { formatTimeRange } from '../../utils/format';
import { toAbsoluteUrl } from '../../utils/url';

type Props = NativeStackScreenProps<RootStackParamList, 'VendorDetail'>;

export function VendorDetailScreen({ navigation, route }: Props) {
  const { vendorId } = route.params;
  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [slots, setSlots] = useState<VendorSlot[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const [food, stationary] = await Promise.all([getVendors('food'), getVendors('stationery')]);
        const v = [...food, ...stationary].find((x) => x.id === vendorId) ?? null;
        setVendor(v);
      } catch (e) {
        Alert.alert('Vendor unavailable', toApiError(e).message);
      }
    })();
  }, [vendorId]);

  useEffect(() => {
    (async () => {
      try {
        const s = await getVendorSlots(vendorId);
        setSlots(s.slice(0, 3));
      } catch (e) {
        // optional preview
      }
    })();
  }, [vendorId]);

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.card}>
          {vendor?.logo_url ? (
            <Image source={{ uri: toAbsoluteUrl(vendor.logo_url) ?? vendor.logo_url }} style={styles.image} />
          ) : (
            <View style={[styles.image, styles.placeholder]}>
              <Text style={styles.placeholderText}>{vendor?.name?.charAt(0) ?? 'V'}</Text>
            </View>
          )}
          <Text style={styles.name}>{vendor?.name ?? 'Vendor'}</Text>
          <Text style={styles.meta}>{vendor?.description ?? 'No description provided.'}</Text>
          <Text style={styles.meta}>Prep: {vendor?.live_load_label ?? '—'}</Text>
          <Text style={styles.meta}>Category: {vendor?.vendor_type ?? '—'}</Text>

          {slots.length > 0 && (
            <View style={styles.slots}>
              <Text style={styles.sectionTitle}>Upcoming Slots</Text>
              {slots.map((s) => (
                <Text key={s.id} style={styles.slotItem}>{formatTimeRange(s.start_time, s.end_time)} • {s.load_label}</Text>
              ))}
            </View>
          )}

          <GradientButton
            label={vendor?.vendor_type === 'stationery' ? 'Start Print' : 'View Menu'}
            onPress={() =>
              vendor?.vendor_type === 'stationery'
                ? navigation.navigate('FileUpload', { vendorId, vendorName: vendor?.name })
                : navigation.navigate('Menu', { vendorId, vendorName: vendor?.name })
            }
          />
        </View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingVertical: 10,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 16,
    shadowColor: 'rgba(0,0,0,0.1)',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 4,
  },
  image: {
    height: 180,
    borderRadius: 14,
    backgroundColor: '#F5F7FB',
    marginBottom: 12,
  },
  placeholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderText: {
    fontSize: 28,
    fontWeight: '800',
    color: '#6C63FF',
  },
  name: {
    fontSize: 18,
    fontWeight: '800',
  },
  meta: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 6,
  },
  slots: {
    marginTop: 12,
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 6,
  },
  slotItem: {
    fontSize: 14,
    color: '#111827',
    marginBottom: 4,
  },
});
