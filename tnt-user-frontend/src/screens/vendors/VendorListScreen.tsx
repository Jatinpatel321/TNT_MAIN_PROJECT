import React, { useEffect, useMemo, useState } from 'react';
import { Alert, FlatList, StyleSheet, TextInput, View } from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../types/navigation';
import type { Vendor, VendorType } from '../../types/models';
import { Screen } from '../../components/Screen';
import { VendorCard } from '../../components/VendorCard';
import { getVendors } from '../../services/vendorService';
import { toApiError } from '../../services/apiClient';

type Props = NativeStackScreenProps<RootStackParamList, 'VendorList'>;

const FILTERS: VendorType[] = ['food', 'stationery'];

export function VendorListScreen({ navigation, route }: Props) {
  const initialType = route.params?.type ?? 'food';
  const [filter, setFilter] = useState<VendorType>(initialType);
  const [search, setSearch] = useState('');
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(false);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return vendors.filter((v) => v.vendor_type === filter && (!term || (v.name ?? '').toLowerCase().includes(term)));
  }, [vendors, filter, search]);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const list = await getVendors(filter);
        setVendors(list);
      } catch (e) {
        Alert.alert('Failed to load vendors', toApiError(e).message);
      } finally {
        setLoading(false);
      }
    })();
  }, [filter]);

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Vendors</Text>
      </View>

      <View style={styles.searchBox}>
        <TextInput
          placeholder="Search vendors"
          placeholderTextColor="#9CA3AF"
          value={search}
          onChangeText={setSearch}
          style={styles.searchInput}
        />
      </View>

      <View style={styles.filterRow}>
        {FILTERS.map((f) => (
          <Text
            key={f}
            style={[styles.filterChip, filter === f && styles.filterChipActive]}
            onPress={() => setFilter(f)}
          >
            {f === 'food' ? 'Food Vendors' : 'Stationery Vendors'}
          </Text>
        ))}
      </View>

      <FlatList
        data={filtered}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <VendorCard
            vendor={item}
            onPress={() => navigation.navigate('VendorDetail', { vendorId: item.id, vendorName: item.name })}
          />
        )}
        numColumns={2}
        columnWrapperStyle={styles.columnWrapper}
        contentContainerStyle={styles.listContent}
        refreshing={loading}
        onRefresh={() => setFilter((prev) => prev)}
        ListEmptyComponent={!loading ? <Text style={styles.muted}>No vendors found.</Text> : null}
        showsVerticalScrollIndicator={false}
      />
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
  searchBox: {
    marginTop: 10,
  },
  searchInput: {
    backgroundColor: '#F5F7FB',
    borderRadius: 12,
    padding: 12,
    fontSize: 14,
    color: '#111827',
  },
  filterRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 12,
    marginBottom: 8,
  },
  filterChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 14,
    backgroundColor: '#F5F7FB',
    color: '#6B7280',
    fontWeight: '600',
  },
  filterChipActive: {
    backgroundColor: '#6C63FF',
    color: '#FFFFFF',
  },
  listContent: {
    paddingTop: 10,
    paddingHorizontal: 16,
    gap: 16,
  },
  columnWrapper: {
    justifyContent: 'space-between',
  },
  muted: {
    color: '#6B7280',
    textAlign: 'center',
    marginTop: 12,
  },
});
