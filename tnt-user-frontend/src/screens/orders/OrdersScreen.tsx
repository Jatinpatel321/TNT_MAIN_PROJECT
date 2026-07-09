import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import {Text} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';

import type {RootStackParamList} from '../../types/navigation';
import type {Order, Vendor} from '../../types/models';
import {Screen} from '../../components/Screen';
import {getOrdersPaged, type OrderSort} from '../../services/orderService';
import {toApiError} from '../../services/apiClient';
import {getVendors} from '../../services/vendorService';
import {OrderHistoryCard} from '../../components/OrderHistoryCard';
import {useAppTheme} from '../../theme/ThemeContext';
import type {AppPalette} from '../../theme/theme';

type Nav = NativeStackNavigationProp<RootStackParamList>;

type StatusGroup = 'active' | 'past';
type OrderTypeFilter = 'all' | 'food' | 'stationery' | 'combined';
type DateFilter = 'all' | '7d' | '30d';

const PAGE_SIZE = 15;

const SORT_LABELS: Record<OrderSort, string> = {
  newest: 'Newest',
  oldest: 'Oldest',
  amount_desc: 'Price high',
  amount_asc: 'Price low',
};
const SORT_ORDER: OrderSort[] = ['newest', 'oldest', 'amount_desc', 'amount_asc'];

const ORDER_TYPES: OrderTypeFilter[] = ['all', 'food', 'stationery', 'combined'];
const DATE_FILTERS: {key: DateFilter; label: string}[] = [
  {key: 'all', label: 'All time'},
  {key: '7d', label: 'Last 7 days'},
  {key: '30d', label: 'Last 30 days'},
];

function dateFromFor(filter: DateFilter): string | undefined {
  if (filter === 'all') return undefined;
  const days = filter === '7d' ? 7 : 30;
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}

export function OrdersScreen() {
  const navigation = useNavigation<Nav>();
  const {colors} = useAppTheme();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [orders, setOrders] = useState<Order[]>([]);
  const [total, setTotal] = useState(0);
  const [vendorMap, setVendorMap] = useState<Record<number, Vendor>>({});

  const [tab, setTab] = useState<StatusGroup>('active');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sort, setSort] = useState<OrderSort>('newest');
  const [orderType, setOrderType] = useState<OrderTypeFilter>('all');
  const [dateFilter, setDateFilter] = useState<DateFilter>('all');

  // Debounce the search box so we don't hit the API on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 350);
    return () => clearTimeout(t);
  }, [search]);

  const query = useMemo(
    () => ({
      status: tab,
      search: debouncedSearch || undefined,
      sort,
      order_type: orderType === 'all' ? undefined : orderType,
      date_from: dateFromFor(dateFilter),
    }),
    [tab, debouncedSearch, sort, orderType, dateFilter],
  );

  const offsetRef = useRef(0);

  const load = useCallback(
    async (reset: boolean) => {
      try {
        if (reset) {
          setLoading(true);
          offsetRef.current = 0;
        } else {
          setLoadingMore(true);
        }
        const page = await getOrdersPaged({
          ...query,
          limit: PAGE_SIZE,
          offset: reset ? 0 : offsetRef.current,
        });
        setTotal(page.total);
        offsetRef.current = (reset ? 0 : offsetRef.current) + page.items.length;
        setOrders(prev => (reset ? page.items : [...prev, ...page.items]));
      } catch (e) {
        Alert.alert('Failed to load orders', toApiError(e).message);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [query],
  );

  // Load vendors once (for logos / names).
  useEffect(() => {
    (async () => {
      try {
        const [food, stationery] = await Promise.all([
          getVendors('food'),
          getVendors('stationery'),
        ]);
        const map: Record<number, Vendor> = {};
        [...food, ...stationery].forEach(v => {
          map[v.id] = v;
        });
        setVendorMap(map);
      } catch {
        // vendor metadata is non-critical
      }
    })();
  }, []);

  // Reload whenever any filter changes.
  useEffect(() => {
    load(true);
  }, [load]);

  const canLoadMore = orders.length < total;

  const onEndReached = () => {
    if (!loading && !loadingMore && canLoadMore) {
      load(false);
    }
  };

  const renderItem = ({item: o}: {item: Order}) => {
    const vendor = vendorMap[o.vendor_id];
    const vendorName = o.vendor_name ?? vendor?.name ?? `Vendor #${o.vendor_id}`;
    const totalRupees =
      typeof o.total_amount === 'number' ? Number(o.total_amount) : null;
    return (
      <OrderHistoryCard
        order={o}
        vendorName={vendorName}
        vendorLogoUrl={vendor?.logo_url ?? null}
        totalAmount={totalRupees}
        onPress={() => navigation.navigate('OrderTracking', {orderId: o.id})}
        onShowQr={() => navigation.navigate('QR', {orderId: o.id})}
      />
    );
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="headlineSmall" style={styles.title}>
          My Orders
        </Text>
        <Text style={styles.sub}>Search, filter and track your orders.</Text>
      </View>

      {/* Search */}
      <View style={styles.searchBox}>
        <TextInput
          placeholder="Search by vendor or item"
          placeholderTextColor={colors.muted}
          value={search}
          onChangeText={setSearch}
          style={styles.searchInput}
        />
      </View>

      {/* Active / Past */}
      <View style={styles.tabRow}>
        <Pressable
          style={[styles.tab, tab === 'active' && styles.tabActive]}
          onPress={() => setTab('active')}>
          <Text style={[styles.tabText, tab === 'active' && styles.tabTextActive]}>
            Active
          </Text>
        </Pressable>
        <Pressable
          style={[styles.tab, tab === 'past' && styles.tabActive]}
          onPress={() => setTab('past')}>
          <Text style={[styles.tabText, tab === 'past' && styles.tabTextActive]}>
            Past
          </Text>
        </Pressable>
      </View>

      {/* Filter chips: order type */}
      <FlatList
        horizontal
        data={ORDER_TYPES}
        keyExtractor={t => t}
        showsHorizontalScrollIndicator={false}
        style={styles.chipRowList}
        contentContainerStyle={styles.chipRow}
        renderItem={({item: t}) => (
          <Pressable
            style={[styles.chip, orderType === t && styles.chipActive]}
            onPress={() => setOrderType(t)}>
            <Text style={[styles.chipText, orderType === t && styles.chipTextActive]}>
              {t === 'all' ? 'All types' : t.charAt(0).toUpperCase() + t.slice(1)}
            </Text>
          </Pressable>
        )}
      />

      {/* Filter chips: date + sort */}
      <View style={styles.filterBar}>
        <View style={styles.dateChips}>
          {DATE_FILTERS.map(df => (
            <Pressable
              key={df.key}
              style={[styles.chip, dateFilter === df.key && styles.chipActive]}
              onPress={() => setDateFilter(df.key)}>
              <Text
                style={[styles.chipText, dateFilter === df.key && styles.chipTextActive]}>
                {df.label}
              </Text>
            </Pressable>
          ))}
        </View>
        <Pressable
          style={styles.sortBtn}
          onPress={() =>
            setSort(prev => SORT_ORDER[(SORT_ORDER.indexOf(prev) + 1) % SORT_ORDER.length])
          }>
          <Text style={styles.sortBtnText}>⇅ {SORT_LABELS[sort]}</Text>
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator />
        </View>
      ) : (
        <FlatList
          data={orders}
          keyExtractor={o => String(o.id)}
          renderItem={renderItem}
          ItemSeparatorComponent={() => <View style={{height: 10}} />}
          contentContainerStyle={styles.listContent}
          onEndReached={onEndReached}
          onEndReachedThreshold={0.4}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyIcon}>📋</Text>
              <Text style={styles.emptyTitle}>No orders found</Text>
              <Text style={styles.emptySub}>Try adjusting your filters or search.</Text>
            </View>
          }
          ListFooterComponent={
            loadingMore ? (
              <View style={styles.center}>
                <ActivityIndicator />
              </View>
            ) : canLoadMore ? (
              <Pressable style={styles.loadMoreBtn} onPress={() => load(false)}>
                <Text style={styles.loadMoreText}>Load more</Text>
              </Pressable>
            ) : null
          }
        />
      )}
    </Screen>
  );
}

const makeStyles = (colors: AppPalette) => StyleSheet.create({
  header: {
    paddingTop: 18,
    paddingBottom: 8,
  },
  title: {
    fontWeight: '900',
    color: colors.text,
  },
  sub: {
    color: colors.muted,
    marginTop: 4,
  },
  searchBox: {
    marginBottom: 10,
  },
  searchInput: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 12,
    padding: 12,
    fontSize: 14,
    color: colors.text,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  tabRow: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceAlt,
    borderRadius: 12,
    padding: 4,
    marginBottom: 10,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 10,
  },
  tabActive: {
    backgroundColor: colors.surface,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: {width: 0, height: 1},
    shadowRadius: 2,
    elevation: 1,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.muted,
  },
  tabTextActive: {
    color: colors.text,
    fontWeight: '700',
  },
  chipRowList: {
    flexGrow: 0,
    marginBottom: 8,
  },
  chipRow: {
    gap: 8,
    paddingRight: 8,
  },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 14,
    backgroundColor: colors.surfaceAlt,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  chipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  chipText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.muted,
  },
  chipTextActive: {
    color: colors.onPrimary,
  },
  filterBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
    gap: 8,
  },
  dateChips: {
    flexDirection: 'row',
    gap: 8,
    flexShrink: 1,
    flexWrap: 'wrap',
  },
  sortBtn: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 14,
    backgroundColor: colors.primarySoft,
  },
  sortBtnText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.primary,
  },
  listContent: {
    paddingBottom: 24,
  },
  center: {
    paddingVertical: 24,
    alignItems: 'center',
  },
  emptyContainer: {
    alignItems: 'center',
    paddingTop: 40,
    gap: 8,
  },
  emptyIcon: {
    fontSize: 48,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.text,
  },
  emptySub: {
    fontSize: 14,
    color: colors.muted,
    textAlign: 'center',
  },
  loadMoreBtn: {
    marginTop: 12,
    alignSelf: 'center',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 14,
    backgroundColor: colors.surfaceAlt,
  },
  loadMoreText: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.primary,
  },
});
