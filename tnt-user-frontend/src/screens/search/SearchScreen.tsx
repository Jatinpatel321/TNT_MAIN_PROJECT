import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  Keyboard,
  Modal,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../types/navigation';
import type {
  SearchItemResult,
  SearchVendorResult,
  SearchFilters,
  SearchSortOption,
} from '../../types/models';
import { Screen } from '../../components/Screen';
import { search, searchSuggestions } from '../../services/searchService';
import { toApiError } from '../../services/apiClient';
import { formatMoneyPaise } from '../../utils/format';

type Nav = NativeStackNavigationProp<RootStackParamList>;

const SORT_OPTIONS: { key: SearchSortOption; label: string; icon: string }[] = [
  { key: 'popular', label: 'Popular', icon: 'fire' },
  { key: 'price_low', label: 'Lowest Price', icon: 'arrow-down' },
  { key: 'price_high', label: 'Highest Price', icon: 'arrow-up' },
  { key: 'fastest', label: 'Fastest', icon: 'lightning-bolt' },
  { key: 'rating', label: 'Top Rated', icon: 'star' },
];

const TYPE_OPTIONS = [
  { key: 'all' as const, label: 'All' },
  { key: 'food' as const, label: 'Food' },
  { key: 'stationery' as const, label: 'Stationery' },
];

const RATING_OPTIONS = [3, 3.5, 4, 4.5];

export function SearchScreen() {
  const navigation = useNavigation<Nav>();
  const [query, setQuery] = useState('');
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [vendors, setVendors] = useState<SearchVendorResult[]>([]);
  const [items, setItems] = useState<SearchItemResult[]>([]);
  const [totalVendors, setTotalVendors] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Filters
  const [filters, setFilters] = useState<SearchFilters>({ sort: 'popular' });
  const [showFilterModal, setShowFilterModal] = useState(false);

  // Temporary filter state for the modal
  const [tempType, setTempType] = useState<'all' | 'food' | 'stationery'>('all');
  const [tempMinRating, setTempMinRating] = useState<number | undefined>(undefined);
  const [tempAvailability, setTempAvailability] = useState(false);
  const [tempPriceMin, setTempPriceMin] = useState('');
  const [tempPriceMax, setTempPriceMax] = useState('');
  const [tempSort, setTempSort] = useState<SearchSortOption>('popular');

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (q: string, f: SearchFilters) => {
    if (!q.trim()) {
      setVendors([]);
      setItems([]);
      setTotalVendors(0);
      setTotalItems(0);
      setSearched(false);
      return;
    }
    setLoading(true);
    try {
      const res = await search(q.trim(), f);
      setVendors(res.vendors);
      setItems(res.items);
      setTotalVendors(res.total_vendors);
      setTotalItems(res.total_items);
      setSearched(true);
      setShowSuggestions(false);
    } catch (e) {
      Alert.alert('Search failed', toApiError(e).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleQueryChange = useCallback((text: string) => {
    setQuery(text);
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!text.trim()) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    // Fetch suggestions with debounce
    debounceRef.current = setTimeout(async () => {
      try {
        const s = await searchSuggestions(text.trim(), 6);
        setSuggestions(s);
        setShowSuggestions(s.length > 0);
      } catch (_) { /* non-fatal */ }
    }, 300);
  }, []);

  const handleSubmit = useCallback(() => {
    Keyboard.dismiss();
    doSearch(query, filters);
  }, [query, filters, doSearch]);

  const applyFilters = useCallback(() => {
    const newFilters: SearchFilters = {
      type: tempType !== 'all' ? tempType : undefined,
      sort: tempSort,
      min_rating: tempMinRating,
      availability: tempAvailability || undefined,
      price_min: tempPriceMin ? parseInt(tempPriceMin, 10) * 100 : undefined,
      price_max: tempPriceMax ? parseInt(tempPriceMax, 10) * 100 : undefined,
    };
    setFilters(newFilters);
    setShowFilterModal(false);
    if (query.trim()) doSearch(query, newFilters);
  }, [tempType, tempSort, tempMinRating, tempAvailability, tempPriceMin, tempPriceMax, query, doSearch]);

  const openFilterModal = useCallback(() => {
    setTempType(filters.type ?? 'all');
    setTempSort(filters.sort ?? 'popular');
    setTempMinRating(filters.min_rating);
    setTempAvailability(filters.availability ?? false);
    setTempPriceMin(filters.price_min != null ? String(Math.round(filters.price_min / 100)) : '');
    setTempPriceMax(filters.price_max != null ? String(Math.round(filters.price_max / 100)) : '');
    setShowFilterModal(true);
  }, [filters]);

  const activeFilterCount = [
    filters.type && filters.type !== 'all',
    filters.min_rating,
    filters.availability,
    filters.price_min,
    filters.price_max,
  ].filter(Boolean).length;

  const renderVendor = ({ item }: { item: SearchVendorResult }) => (
    <Pressable
      style={styles.vendorCard}
      onPress={() => navigation.navigate('VendorDetail', { vendorId: item.id, vendorName: item.name })}
    >
      {item.logo_url ? (
        <Image source={{ uri: item.logo_url }} style={styles.vendorImage} />
      ) : (
        <View style={styles.vendorImagePlaceholder}>
          <MaterialCommunityIcons name="store" size={24} color="#6C63FF" />
        </View>
      )}
      <View style={styles.vendorInfo}>
        <Text style={styles.vendorName} numberOfLines={1}>{item.name ?? `Vendor #${item.id}`}</Text>
        <View style={styles.chipRow}>
          <View style={styles.chip}>
            <Text style={styles.chipText}>{item.vendor_type.toUpperCase()}</Text>
          </View>
          <Text style={styles.ratingText}>⭐ {item.rating.toFixed(1)}</Text>
          {item.category && (
            <Text style={styles.categoryText}>{item.category}</Text>
          )}
        </View>
        <Text style={styles.loadText}>Load: {item.live_load_label}</Text>
      </View>
    </Pressable>
  );

  const renderItem = ({ item }: { item: SearchItemResult }) => (
    <Pressable
      style={styles.itemCard}
      onPress={() => {
        if (item.item_type === 'food') {
          navigation.navigate('Menu', { vendorId: item.vendor_id, vendorName: item.vendor_name });
        } else {
          navigation.navigate('VendorDetail', { vendorId: item.vendor_id, vendorName: item.vendor_name });
        }
      }}
    >
      {item.image_url ? (
        <Image source={{ uri: item.image_url }} style={styles.itemImage} />
      ) : (
        <View style={styles.itemImagePlaceholder}>
          <MaterialCommunityIcons
            name={item.item_type === 'food' ? 'food' : 'printer'}
            size={20}
            color="#6C63FF"
          />
        </View>
      )}
      <View style={styles.itemInfo}>
        <Text style={styles.itemName} numberOfLines={1}>{item.name}</Text>
        <Text style={styles.itemVendor} numberOfLines={1}>{item.vendor_name ?? `Vendor #${item.vendor_id}`}</Text>
        <View style={styles.itemMetaRow}>
          <Text style={styles.itemPrice}>{formatMoneyPaise(item.price)}{item.unit ? ` / ${item.unit}` : ''}</Text>
          {item.is_available ? (
            <Text style={styles.availableText}>Available</Text>
          ) : (
            <Text style={styles.unavailableText}>Unavailable</Text>
          )}
        </View>
        <View style={styles.chipRow}>
          <View style={[styles.chip, item.item_type === 'food' ? styles.chipFood : styles.chipStationery]}>
            <Text style={[styles.chipText, item.item_type === 'food' ? styles.chipTextFood : styles.chipTextStationery]}>
              {item.item_type === 'food' ? 'Food' : 'Stationery'}
            </Text>
          </View>
          <Text style={styles.ratingText}>⭐ {item.vendor_rating.toFixed(1)}</Text>
        </View>
      </View>
    </Pressable>
  );

  return (
    <Screen>
      {/* Search bar */}
      <View style={styles.searchRow}>
        <View style={styles.searchBar}>
          <MaterialCommunityIcons name="magnify" size={20} color="#9CA3AF" />
          <TextInput
            style={styles.searchInput}
            placeholder="Search vendors, food, stationery..."
            placeholderTextColor="#9CA3AF"
            value={query}
            onChangeText={handleQueryChange}
            onSubmitEditing={handleSubmit}
            returnKeyType="search"
            autoFocus
          />
          {query.length > 0 && (
            <Pressable onPress={() => { setQuery(''); setSuggestions([]); setShowSuggestions(false); }}>
              <MaterialCommunityIcons name="close-circle" size={18} color="#9CA3AF" />
            </Pressable>
          )}
        </View>
        <Pressable style={styles.filterButton} onPress={openFilterModal}>
          <MaterialCommunityIcons name="tune-vertical" size={20} color="#6C63FF" />
          {activeFilterCount > 0 && (
            <View style={styles.filterBadge}>
              <Text style={styles.filterBadgeText}>{activeFilterCount}</Text>
            </View>
          )}
        </Pressable>
      </View>

      {/* Sort bar */}
      <View style={styles.sortRow}>
        {SORT_OPTIONS.map((opt) => (
          <Pressable
            key={opt.key}
            style={[styles.sortChip, filters.sort === opt.key && styles.sortChipActive]}
            onPress={() => {
              const newFilters = { ...filters, sort: opt.key };
              setFilters(newFilters);
              if (query.trim()) doSearch(query, newFilters);
            }}
          >
            <MaterialCommunityIcons
              name={opt.icon}
              size={14}
              color={filters.sort === opt.key ? '#FFFFFF' : '#6B7280'}
            />
            <Text style={[styles.sortChipText, filters.sort === opt.key && styles.sortChipTextActive]}>
              {opt.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Suggestions overlay */}
      {showSuggestions && suggestions.length > 0 && (
        <View style={styles.suggestionsContainer}>
          {suggestions.map((s, i) => (
            <Pressable
              key={`${s}-${i}`}
              style={styles.suggestionItem}
              onPress={() => {
                setQuery(s);
                setShowSuggestions(false);
                doSearch(s, filters);
              }}
            >
              <MaterialCommunityIcons name="magnify" size={16} color="#9CA3AF" />
              <Text style={styles.suggestionText}>{s}</Text>
            </Pressable>
          ))}
        </View>
      )}

      {/* Results */}
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#6C63FF" />
        </View>
      ) : !searched ? (
        <View style={styles.center}>
          <MaterialCommunityIcons name="magnify" size={48} color="#D1D5DB" />
          <Text style={styles.emptyTitle}>Search for anything</Text>
          <Text style={styles.emptySubtitle}>Vendors, food items, stationery services...</Text>
        </View>
      ) : vendors.length === 0 && items.length === 0 ? (
        <View style={styles.center}>
          <MaterialCommunityIcons name="emoticon-sad-outline" size={48} color="#D1D5DB" />
          <Text style={styles.emptyTitle}>No results found</Text>
          <Text style={styles.emptySubtitle}>Try a different search term or adjust filters</Text>
        </View>
      ) : (
        <FlatList
          data={[] as any}
          keyExtractor={() => 'header'}
          renderItem={() => null}
          ListHeaderComponent={
            <View>
              {vendors.length > 0 && (
                <View style={styles.section}>
                  <Text style={styles.sectionTitle}>Vendors ({totalVendors})</Text>
                  {vendors.map((v) => (
                    <View key={`v-${v.id}`}>{renderVendor({ item: v })}</View>
                  ))}
                </View>
              )}
              {items.length > 0 && (
                <View style={styles.section}>
                  <Text style={styles.sectionTitle}>Items ({totalItems})</Text>
                  {items.map((item) => (
                    <View key={`i-${item.item_type}-${item.id}`}>{renderItem({ item })}</View>
                  ))}
                </View>
              )}
            </View>
          }
          showsVerticalScrollIndicator={false}
        />
      )}

      {/* Filter Modal */}
      <Modal visible={showFilterModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Filters</Text>
              <Pressable onPress={() => setShowFilterModal(false)} hitSlop={8}>
                <MaterialCommunityIcons name="close" size={24} color="#374151" />
              </Pressable>
            </View>

            {/* Type filter */}
            <Text style={styles.filterLabel}>Type</Text>
            <View style={styles.filterOptionRow}>
              {TYPE_OPTIONS.map((opt) => (
                <Pressable
                  key={opt.key}
                  style={[styles.typeChip, tempType === opt.key && styles.typeChipActive]}
                  onPress={() => setTempType(opt.key)}
                >
                  <Text style={[styles.typeChipText, tempType === opt.key && styles.typeChipTextActive]}>
                    {opt.label}
                  </Text>
                </Pressable>
              ))}
            </View>

            {/* Sort */}
            <Text style={styles.filterLabel}>Sort By</Text>
            <View style={styles.filterOptionRow}>
              {SORT_OPTIONS.map((opt) => (
                <Pressable
                  key={opt.key}
                  style={[styles.typeChip, tempSort === opt.key && styles.typeChipActive]}
                  onPress={() => setTempSort(opt.key)}
                >
                  <Text style={[styles.typeChipText, tempSort === opt.key && styles.typeChipTextActive]}>
                    {opt.label}
                  </Text>
                </Pressable>
              ))}
            </View>

            {/* Price range */}
            <Text style={styles.filterLabel}>Price Range (in rupees)</Text>
            <View style={styles.priceRow}>
              <TextInput
                style={styles.priceInput}
                placeholder="Min"
                placeholderTextColor="#9CA3AF"
                value={tempPriceMin}
                onChangeText={setTempPriceMin}
                keyboardType="number-pad"
              />
              <Text style={styles.priceSeparator}>—</Text>
              <TextInput
                style={styles.priceInput}
                placeholder="Max"
                placeholderTextColor="#9CA3AF"
                value={tempPriceMax}
                onChangeText={setTempPriceMax}
                keyboardType="number-pad"
              />
            </View>

            {/* Rating */}
            <Text style={styles.filterLabel}>Minimum Rating</Text>
            <View style={styles.filterOptionRow}>
              {RATING_OPTIONS.map((r) => (
                <Pressable
                  key={r}
                  style={[styles.typeChip, tempMinRating === r && styles.typeChipActive]}
                  onPress={() => setTempMinRating(tempMinRating === r ? undefined : r)}
                >
                  <Text style={[styles.typeChipText, tempMinRating === r && styles.typeChipTextActive]}>
                    ⭐ {r}+
                  </Text>
                </Pressable>
              ))}
            </View>

            {/* Availability */}
            <Pressable
              style={styles.availabilityRow}
              onPress={() => setTempAvailability(!tempAvailability)}
            >
              <Text style={styles.filterLabel}>Only show available</Text>
              <View style={[styles.toggle, tempAvailability && styles.toggleActive]}>
                <View style={[styles.toggleKnob, tempAvailability && styles.toggleKnobActive]} />
              </View>
            </Pressable>

            {/* Apply button */}
            <Pressable style={styles.applyButton} onPress={applyFilters}>
              <Text style={styles.applyButtonText}>Apply Filters</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingTop: 10,
    paddingBottom: 8,
  },
  searchBar: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F5F7FB',
    borderRadius: 14,
    paddingHorizontal: 12,
    height: 46,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    color: '#111827',
    paddingVertical: 0,
  },
  filterButton: {
    position: 'relative',
    width: 46,
    height: 46,
    borderRadius: 14,
    backgroundColor: '#F5F7FB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  filterBadge: {
    position: 'absolute',
    top: -4,
    right: -4,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: '#6C63FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  filterBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  sortRow: {
    flexDirection: 'row',
    gap: 6,
    paddingBottom: 10,
  },
  sortChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 14,
    backgroundColor: '#F5F7FB',
  },
  sortChipActive: {
    backgroundColor: '#6C63FF',
  },
  sortChipText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6B7280',
  },
  sortChipTextActive: {
    color: '#FFFFFF',
  },
  suggestionsContainer: {
    position: 'absolute',
    top: 104,
    left: 16,
    right: 16,
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    zIndex: 100,
    elevation: 8,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
  },
  suggestionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  suggestionText: {
    fontSize: 14,
    color: '#374151',
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#374151',
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 10,
  },
  // Vendor card
  vendorCard: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#F3F4F6',
    gap: 12,
  },
  vendorImage: {
    width: 56,
    height: 56,
    borderRadius: 12,
    backgroundColor: '#F5F7FB',
  },
  vendorImagePlaceholder: {
    width: 56,
    height: 56,
    borderRadius: 12,
    backgroundColor: '#F3F2FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  vendorInfo: {
    flex: 1,
    gap: 2,
  },
  vendorName: {
    fontSize: 15,
    fontWeight: '700',
    color: '#111827',
  },
  loadText: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  // Item card
  itemCard: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#F3F4F6',
    gap: 12,
  },
  itemImage: {
    width: 56,
    height: 56,
    borderRadius: 12,
    backgroundColor: '#F5F7FB',
  },
  itemImagePlaceholder: {
    width: 56,
    height: 56,
    borderRadius: 12,
    backgroundColor: '#F3F2FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemInfo: {
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
  itemMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 2,
  },
  itemPrice: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
  },
  availableText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#059669',
  },
  unavailableText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#DC2626',
  },
  // Chips
  chipRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 2,
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
  chipFood: {
    backgroundColor: '#FEF3C7',
  },
  chipTextFood: {
    color: '#D97706',
  },
  chipStationery: {
    backgroundColor: '#DBEAFE',
  },
  chipTextStationery: {
    color: '#2563EB',
  },
  ratingText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#6B7280',
  },
  categoryText: {
    fontSize: 11,
    color: '#9CA3AF',
  },
  // Modal
  modalOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '800',
  },
  filterLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
    marginTop: 4,
  },
  filterOptionRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 16,
    flexWrap: 'wrap',
  },
  typeChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 14,
    backgroundColor: '#F5F7FB',
  },
  typeChipActive: {
    backgroundColor: '#6C63FF',
  },
  typeChipText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
  },
  typeChipTextActive: {
    color: '#FFFFFF',
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 16,
  },
  priceInput: {
    flex: 1,
    backgroundColor: '#F5F7FB',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 15,
    color: '#111827',
  },
  priceSeparator: {
    fontSize: 16,
    color: '#9CA3AF',
  },
  availabilityRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  toggle: {
    width: 44,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#D1D5DB',
    padding: 2,
  },
  toggleActive: {
    backgroundColor: '#6C63FF',
  },
  toggleKnob: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#FFFFFF',
  },
  toggleKnobActive: {
    marginLeft: 20,
  },
  applyButton: {
    backgroundColor: '#6C63FF',
    borderRadius: 14,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  applyButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
});
