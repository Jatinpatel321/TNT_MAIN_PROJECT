import React, { useEffect, useState } from 'react';
import { Alert, Image, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { Text } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import type { RootStackParamList } from '../../types/navigation';
import type { Vendor, Order } from '../../types/models';
import { Screen } from '../../components/Screen';
import { DealsCarousel } from '../../components/DealsCarousel';
import { ShortcutCard } from '../../components/ShortcutCard';
import { VendorCard } from '../../components/VendorCard';
import { RecentOrderCard } from '../../components/RecentOrderCard';
import { getVendors } from '../../services/vendorService';
import { getMyOrders } from '../../services/orderService';
import { toApiError } from '../../services/apiClient';
import { LOGO } from '../../assets';
import { useAuth } from '../../hooks/useAuth';
import {
  getVendorRecommendations,
  getMenuSuggestions,
  getPopularNearby,
  getPeakHourAlerts,
  getSmartRecommendations,
  recordInteraction,
} from '../../services/recommendationService';
import type {
  VendorRecommendationItem,
  MenuSuggestionItem,
  PopularNearbyVendor,
  PeakHourAlertData,
  SmartRecommendationItem,
  SmartVendorItem,
  SmartRecommendationsResponse,
} from '../../services/recommendationService';
import { toAbsoluteUrl } from '../../utils/url';
import { formatMoneyPaise } from '../../utils/format';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const { user } = useAuth();
  const [popularVendors, setPopularVendors] = useState<Vendor[]>([]);
  const [vendorMap, setVendorMap] = useState<Record<number, string>>({});
  const [recentOrders, setRecentOrders] = useState<Order[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(false);

  const [vendorRecs, setVendorRecs] = useState<VendorRecommendationItem[]>([]);
  const [menuPersonalized, setMenuPersonalized] = useState<MenuSuggestionItem[]>([]);
  const [menuTrending, setMenuTrending] = useState<MenuSuggestionItem[]>([]);
  const [popularNearbyFood, setPopularNearbyFood] = useState<PopularNearbyVendor[]>([]);
  const [popularNearbyStationery, setPopularNearbyStationery] = useState<PopularNearbyVendor[]>([]);
  const [peakAlert, setPeakAlert] = useState<PeakHourAlertData | null>(null);
  const [smartRecs, setSmartRecs] = useState<SmartRecommendationsResponse | null>(null);
  const [frequentlyOrdered, setFrequentlyOrdered] = useState<SmartRecommendationItem[]>([]);
  const [becauseYouOrdered, setBecauseYouOrdered] = useState<SmartRecommendationItem[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const [foodVendors, stationeryVendors] = await Promise.all([
          getVendors('food'),
          getVendors('stationery'),
        ]);
        setPopularVendors(foodVendors.slice(0, 6));
        const map: Record<number, string> = {};
        [...foodVendors, ...stationeryVendors].forEach((v) => {
          map[v.id] = v.name ?? `Vendor #${v.id}`;
        });
        setVendorMap(map);
      } catch (e) {
        Alert.alert('Vendors unavailable', toApiError(e).message);
      }

      try {
        const [vRecs, mSugs, pop, peak, smart] = await Promise.all([
          getVendorRecommendations().catch(() => null),
          getMenuSuggestions().catch(() => null),
          getPopularNearby().catch(() => null),
          getPeakHourAlerts().catch(() => null),
          getSmartRecommendations().catch(() => null),
        ]);
        if (vRecs) setVendorRecs(vRecs.recommendations.slice(0, 5));
        if (mSugs) {
          setMenuPersonalized(mSugs.personalized.slice(0, 10));
          setMenuTrending(mSugs.trending.slice(0, 10));
        }
        if (pop) {
          setPopularNearbyFood(pop.food_vendors.slice(0, 6));
          setPopularNearbyStationery(pop.stationery_vendors.slice(0, 6));
        }
        if (peak) setPeakAlert(peak);
        if (smart) {
          setSmartRecs(smart);
          setFrequentlyOrdered(smart.frequently_ordered.slice(0, 8));
          setBecauseYouOrdered(smart.because_you_ordered.slice(0, 6));
        }
      } catch { /* non-fatal */ }

      try {
        setLoadingOrders(true);
        const orders = await getMyOrders();
        const sorted = [...orders].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
        setRecentOrders(sorted.slice(0, 5));
      } catch (e) {
        Alert.alert('Orders unavailable', toApiError(e).message);
      } finally {
        setLoadingOrders(false);
      }
    })();
  }, []);

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <View style={styles.brandRow}>
            <Image source={LOGO} style={styles.brandLogo} resizeMode="contain" />
            <View>
              <Text style={styles.brandTitle}>Tap N Take</Text>
              <Text style={styles.subtitle}>Schedule smarter. Pick up faster.</Text>
            </View>
          </View>
          <View style={styles.iconRow}>
            <MaterialCommunityIcons
              name="magnify"
              size={26}
              color="#3B82F6"
              onPress={() => navigation.navigate('Search')}
            />
            <MaterialCommunityIcons
              name="bell-outline"
              size={26}
              color="#3B82F6"
              onPress={() => navigation.navigate('NotificationsTab' as any)}
            />
          </View>
        </View>

        <View style={styles.sectionSpacing}>
          <DealsCarousel />
        </View>

        <View style={styles.shortcutsRow}>
          <ShortcutCard
            title="Food Scheduling"
            subtitle="Order Food"
            icon="silverware-fork-knife"
            onPress={() => navigation.navigate('VendorList', { type: 'food' })}
          />
          <ShortcutCard
            title="Stationery Scheduling"
            subtitle="Print & Xerox"
            icon="file-document-outline"
            onPress={() => navigation.navigate('VendorList', { type: 'stationery' })}
          />
        </View>

        {/* Peak Hour Alert Banner */}
        {peakAlert && (
          <TouchableOpacity
            style={[
              styles.peakBanner,
              peakAlert.is_peak_now ? styles.peakBannerActive : styles.peakBannerClear,
            ]}
            onPress={() => navigation.navigate('BestTime')}
            activeOpacity={0.7}
          >
            <MaterialCommunityIcons
              name={peakAlert.is_peak_now ? 'alert-circle' : 'check-circle'}
              size={20}
              color={peakAlert.is_peak_now ? '#DC2626' : '#059669'}
            />
            <View style={styles.peakBannerContent}>
              <Text
                style={[
                  styles.peakBannerTitle,
                  { color: peakAlert.is_peak_now ? '#DC2626' : '#059669' },
                ]}
              >
                {peakAlert.is_peak_now ? 'Peak Hour Active' : 'Off-Peak Now'}
              </Text>
              <Text style={styles.peakBannerAction} numberOfLines={1}>
                {peakAlert.suggested_action}
              </Text>
            </View>
            <MaterialCommunityIcons name="chevron-right" size={20} color="#9CA3AF" />
          </TouchableOpacity>
        )}

        {/* AI Shortcut Cards */}
        <View style={styles.aiShortcutsRow}>
          <TouchableOpacity
            style={styles.aiShortcutCard}
            onPress={() => navigation.navigate('RecommendedForYou')}
            activeOpacity={0.7}
          >
            <View style={[styles.aiShortcutIcon, { backgroundColor: '#EFF6FF' }]}>
              <MaterialCommunityIcons name="robot-happy" size={22} color="#2563EB" />
            </View>
            <Text style={styles.aiShortcutTitle}>Recommended For You</Text>
            <Text style={styles.aiShortcutSub}>Personalized picks</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.aiShortcutCard}
            onPress={() => navigation.navigate('SmartReorder')}
            activeOpacity={0.7}
          >
            <View style={[styles.aiShortcutIcon, { backgroundColor: '#F0FDF4' }]}>
              <MaterialCommunityIcons name="basket-outline" size={22} color="#059669" />
            </View>
            <Text style={styles.aiShortcutTitle}>Smart Reorder</Text>
            <Text style={styles.aiShortcutSub}>Quick repeat orders</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.aiShortcutCard}
            onPress={() => navigation.navigate('BestTime')}
            activeOpacity={0.7}
          >
            <View style={[styles.aiShortcutIcon, { backgroundColor: '#FFF7ED' }]}>
              <MaterialCommunityIcons name="clock-fast" size={22} color="#D97706" />
            </View>
            <Text style={styles.aiShortcutTitle}>Best Time</Text>
            <Text style={styles.aiShortcutSub}>Avoid the rush</Text>
          </TouchableOpacity>
        </View>

        {/* Vendor Recommendations */}
        {vendorRecs.length > 0 && (
          <View style={styles.aiCard}>
            <View style={styles.aiHeader}>
              <MaterialCommunityIcons name="robot-happy" size={20} color="#2563EB" />
              <Text style={styles.aiTitle}>Top Vendors For You</Text>
              <TouchableOpacity onPress={() => navigation.navigate('RecommendedForYou')}>
                <Text style={styles.seeAll}>See All</Text>
              </TouchableOpacity>
            </View>
            {vendorRecs.slice(0, 3).map((v) => (
              <TouchableOpacity
                key={v.vendor_id}
                style={styles.vendorRecCard}
                onPress={() => navigation.navigate('Menu', { vendorId: v.vendor_id, vendorName: v.vendor_name })}
              >
                <View style={[styles.vendorRecIcon, { backgroundColor: v.vendor_type === 'food' ? '#D1FAE5' : '#DBEAFE' }]}>
                  <MaterialCommunityIcons
                    name={v.vendor_type === 'food' ? 'silverware-fork-knife' : 'file-document-outline'}
                    size={18}
                    color={v.vendor_type === 'food' ? '#059669' : '#2563EB'}
                  />
                </View>
                <View style={styles.vendorRecContent}>
                  <Text style={styles.vendorRecName}>{v.vendor_name}</Text>
                  <Text style={styles.vendorRecReason} numberOfLines={1}>{v.reason}</Text>
                </View>
                <View style={styles.vendorRecRight}>
                  <View style={[styles.loadBadge, { backgroundColor: v.live_load === 'LOW' ? '#D1FAE5' : v.live_load === 'MEDIUM' ? '#FEF3C7' : '#FEE2E2' }]}>
                    <Text style={[styles.loadBadgeText, { color: v.live_load === 'LOW' ? '#059669' : v.live_load === 'MEDIUM' ? '#D97706' : '#DC2626' }]}>
                      {v.live_load}
                    </Text>
                  </View>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* Frequently Ordered */}
        {frequentlyOrdered.length > 0 && (
          <View style={[styles.aiCard, styles.frequentCard]}>
            <View style={styles.aiHeader}>
              <MaterialCommunityIcons name="history" size={20} color="#7C3AED" />
              <Text style={[styles.aiTitle, styles.frequentTitle]}>Frequently Ordered</Text>
              <TouchableOpacity onPress={() => navigation.navigate('RecommendedForYou')}>
                <Text style={styles.seeAll}>See All</Text>
              </TouchableOpacity>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.recoRow}>
              {frequentlyOrdered.map((item) => {
                const remoteUri = toAbsoluteUrl(item.image_url);
                const source = remoteUri ? { uri: remoteUri } : null;
                return (
                  <TouchableOpacity
                    key={`fo-${item.id}`}
                    style={styles.recoCard}
                    onPress={() => item.vendor_id && navigation.navigate('Menu', { vendorId: item.vendor_id, vendorName: vendorMap[item.vendor_id] || `Vendor #${item.vendor_id}` })}
                  >
                    {source ? (
                      <Image source={source} style={styles.recoImage} />
                    ) : (
                      <View style={styles.recoImagePlaceholder}>
                        <MaterialCommunityIcons name="food" size={22} color="#D1D5DB" />
                      </View>
                    )}
                    <Text style={styles.recoName} numberOfLines={1}>{item.name}</Text>
                    <Text style={styles.recoMeta} numberOfLines={1}>
                      {item.vendor_id ? vendorMap[item.vendor_id] || `Vendor #${item.vendor_id}` : ''} · {formatMoneyPaise(item.price || 0)}
                    </Text>
                    <Text style={styles.recoReason} numberOfLines={1}>{item.reason}</Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </View>
        )}

        {/* Personalized Menu Suggestions */}
        {menuPersonalized.length > 0 && (
          <View style={[styles.aiCard, styles.personalizedCard]}>
            <View style={styles.aiHeader}>
              <MaterialCommunityIcons name="star-shooting" size={20} color="#0891B2" />
              <Text style={[styles.aiTitle, styles.personalizedTitle]}>Picked For You</Text>
              <TouchableOpacity onPress={() => navigation.navigate('RecommendedForYou')}>
                <Text style={styles.seeAll}>See All</Text>
              </TouchableOpacity>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.recoRow}>
              {menuPersonalized.map((item) => {
                const remoteUri = toAbsoluteUrl(item.image_url);
                const source = remoteUri ? { uri: remoteUri } : null;
                return (
                  <TouchableOpacity
                    key={`p-${item.item_id}`}
                    style={styles.recoCard}
                    onPress={() => navigation.navigate('Menu', { vendorId: item.vendor_id, vendorName: item.vendor_name })}
                  >
                    {source ? (
                      <Image source={source} style={styles.recoImage} />
                    ) : (
                      <View style={styles.recoImagePlaceholder}>
                        <MaterialCommunityIcons name="food" size={22} color="#D1D5DB" />
                      </View>
                    )}
                    <Text style={styles.recoName} numberOfLines={1}>{item.item_name}</Text>
                    <Text style={styles.recoMeta} numberOfLines={1}>
                      {item.vendor_name} · {formatMoneyPaise(item.price_paise)}
                    </Text>
                    <Text style={styles.recoReason} numberOfLines={1}>{item.reason}</Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </View>
        )}

        {/* Trending on Campus */}
        {menuTrending.length > 0 && (
          <View style={[styles.aiCard, styles.trendingCard]}>
            <View style={styles.aiHeader}>
              <MaterialCommunityIcons name="fire" size={20} color="#D97706" />
              <Text style={[styles.aiTitle, styles.trendingTitle]}>Trending Near You</Text>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.recoRow}>
              {menuTrending.map((item) => {
                const remoteUri = toAbsoluteUrl(item.image_url);
                const source = remoteUri ? { uri: remoteUri } : null;
                return (
                  <TouchableOpacity
                    key={`t-${item.item_id}`}
                    style={styles.recoCard}
                    onPress={() => navigation.navigate('Menu', { vendorId: item.vendor_id, vendorName: item.vendor_name })}
                  >
                    {source ? (
                      <Image source={source} style={styles.recoImage} />
                    ) : (
                      <View style={styles.recoImagePlaceholder}>
                        <MaterialCommunityIcons name="food" size={22} color="#D1D5DB" />
                      </View>
                    )}
                    <Text style={styles.recoName} numberOfLines={1}>{item.item_name}</Text>
                    <Text style={styles.recoMeta} numberOfLines={1}>
                      {item.vendor_name} · {formatMoneyPaise(item.price_paise)}
                    </Text>
                    <Text style={styles.recoReasonTrending} numberOfLines={1}>{item.reason}</Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </View>
        )}

        {/* Because You Ordered */}
        {becauseYouOrdered.length > 0 && (
          <View style={[styles.aiCard, styles.becauseCard]}>
            <View style={styles.aiHeader}>
              <MaterialCommunityIcons name="link-variant" size={20} color="#DB2777" />
              <Text style={[styles.aiTitle, styles.becauseTitle]}>Because You Ordered</Text>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.recoRow}>
              {becauseYouOrdered.map((item) => {
                const remoteUri = toAbsoluteUrl(item.image_url);
                const source = remoteUri ? { uri: remoteUri } : null;
                return (
                  <TouchableOpacity
                    key={`byo-${item.id}`}
                    style={styles.recoCard}
                    onPress={() => item.vendor_id && navigation.navigate('Menu', { vendorId: item.vendor_id, vendorName: vendorMap[item.vendor_id] || `Vendor #${item.vendor_id}` })}
                  >
                    {source ? (
                      <Image source={source} style={styles.recoImage} />
                    ) : (
                      <View style={styles.recoImagePlaceholder}>
                        <MaterialCommunityIcons name="food" size={22} color="#D1D5DB" />
                      </View>
                    )}
                    <Text style={styles.recoName} numberOfLines={1}>{item.name}</Text>
                    <Text style={styles.recoMeta} numberOfLines={1}>
                      {item.vendor_id ? vendorMap[item.vendor_id] || `Vendor #${item.vendor_id}` : ''} · {formatMoneyPaise(item.price || 0)}
                    </Text>
                    <Text style={[styles.recoReason, styles.becauseReason]} numberOfLines={1}>{item.reason}</Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </View>
        )}

        {/* Popular Near You */}
        {(popularNearbyFood.length > 0 || popularNearbyStationery.length > 0) && (
          <View style={styles.aiCard}>
            <View style={styles.aiHeader}>
              <MaterialCommunityIcons name="map-marker-radius" size={20} color="#059669" />
              <Text style={styles.aiTitle}>Popular Near You</Text>
            </View>
            {popularNearbyFood.length > 0 && (
              <View style={styles.popularSection}>
                <Text style={styles.popularLabel}>Food</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.recoRow}>
                  {popularNearbyFood.map((v) => (
                    <TouchableOpacity
                      key={`pf-${v.vendor_id}`}
                      style={styles.popularCard}
                      onPress={() => navigation.navigate('Menu', { vendorId: v.vendor_id, vendorName: v.vendor_name })}
                    >
                      <View style={styles.popularIconWrap}>
                        <MaterialCommunityIcons name="silverware-fork-knife" size={20} color="#059669" />
                      </View>
                      <Text style={styles.popularName} numberOfLines={1}>{v.vendor_name}</Text>
                      <View style={styles.popularStats}>
                        <Text style={styles.popularOrders}>{v.order_count} orders</Text>
                        {v.avg_rating > 0 && (
                          <View style={styles.popularRating}>
                            <MaterialCommunityIcons name="star" size={12} color="#FBBF24" />
                            <Text style={styles.popularRatingText}>{v.avg_rating.toFixed(1)}</Text>
                          </View>
                        )}
                      </View>
                      <View style={[styles.loadBadge, { backgroundColor: v.live_load === 'LOW' ? '#D1FAE5' : v.live_load === 'MEDIUM' ? '#FEF3C7' : '#FEE2E2' }]}>
                        <Text style={[styles.loadBadgeText, { color: v.live_load === 'LOW' ? '#059669' : v.live_load === 'MEDIUM' ? '#D97706' : '#DC2626' }]}>
                          {v.live_load}
                        </Text>
                      </View>
                    </TouchableOpacity>
                  ))}
                </ScrollView>
              </View>
            )}
            {popularNearbyStationery.length > 0 && (
              <View style={styles.popularSection}>
                <Text style={styles.popularLabel}>Stationery</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.recoRow}>
                  {popularNearbyStationery.map((v) => (
                    <TouchableOpacity
                      key={`ps-${v.vendor_id}`}
                      style={styles.popularCard}
                      onPress={() => navigation.navigate('Menu', { vendorId: v.vendor_id, vendorName: v.vendor_name })}
                    >
                      <View style={[styles.popularIconWrap, { backgroundColor: '#DBEAFE' }]}>
                        <MaterialCommunityIcons name="file-document-outline" size={20} color="#2563EB" />
                      </View>
                      <Text style={styles.popularName} numberOfLines={1}>{v.vendor_name}</Text>
                      <View style={styles.popularStats}>
                        <Text style={styles.popularOrders}>{v.order_count} orders</Text>
                        {v.avg_rating > 0 && (
                          <View style={styles.popularRating}>
                            <MaterialCommunityIcons name="star" size={12} color="#FBBF24" />
                            <Text style={styles.popularRatingText}>{v.avg_rating.toFixed(1)}</Text>
                          </View>
                        )}
                      </View>
                      <View style={[styles.loadBadge, { backgroundColor: v.live_load === 'LOW' ? '#D1FAE5' : v.live_load === 'MEDIUM' ? '#FEF3C7' : '#FEE2E2' }]}>
                        <Text style={[styles.loadBadgeText, { color: v.live_load === 'LOW' ? '#059669' : v.live_load === 'MEDIUM' ? '#D97706' : '#DC2626' }]}>
                          {v.live_load}
                        </Text>
                      </View>
                    </TouchableOpacity>
                  ))}
                </ScrollView>
              </View>
            )}
          </View>
        )}

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Popular Vendors</Text>
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.horizontalList}>
          {popularVendors.map((v) => (
            <VendorCard key={v.id} vendor={v} onPress={() => navigation.navigate('Menu', { vendorId: v.id, vendorName: v.name })} />
          ))}
          {popularVendors.length === 0 && <Text style={styles.muted}>No vendors available.</Text>}
        </ScrollView>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Recent Orders</Text>
        </View>
        {loadingOrders ? (
          <Text style={styles.muted}>Loading...</Text>
        ) : recentOrders.length === 0 ? (
          <Text style={styles.muted}>No recent orders.</Text>
        ) : (
          recentOrders.map((o) => (
            <RecentOrderCard
              key={o.id}
              order={o}
              vendorName={vendorMap[o.vendor_id] ?? `Vendor #${o.vendor_id}`}
              onPress={() => navigation.navigate('OrderTracking', { orderId: o.id })}
            />
          ))
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: 20,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 10,
    paddingBottom: 10,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  brandLogo: {
    width: 32,
    height: 32,
  },
  brandTitle: {
    fontSize: 16,
    fontWeight: '800',
  },
  iconRow: {
    flexDirection: 'row',
    gap: 16,
  },
  subtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  sectionSpacing: {
    marginTop: 20,
  },
  shortcutsRow: {
    marginTop: 20,
    flexDirection: 'row',
    gap: 10,
  },
  sectionHeader: {
    marginTop: 20,
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  horizontalList: {
    paddingBottom: 4,
  },
  muted: {
    fontSize: 14,
    color: '#6B7280',
  },
  seeAll: {
    fontSize: 13,
    fontWeight: '600',
    color: '#3B82F6',
    marginLeft: 'auto',
  },

  // Peak hour banner
  peakBanner: {
    marginTop: 16,
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 14,
    padding: 12,
    gap: 10,
  },
  peakBannerActive: {
    backgroundColor: '#FEF2F2',
    borderWidth: 1,
    borderColor: '#FECACA',
  },
  peakBannerClear: {
    backgroundColor: '#F0FDF4',
    borderWidth: 1,
    borderColor: '#BBF7D0',
  },
  peakBannerContent: {
    flex: 1,
    gap: 1,
  },
  peakBannerTitle: {
    fontSize: 14,
    fontWeight: '700',
  },
  peakBannerAction: {
    fontSize: 12,
    color: '#4B5563',
  },

  // AI shortcut cards
  aiShortcutsRow: {
    marginTop: 16,
    flexDirection: 'row',
    gap: 8,
  },
  aiShortcutCard: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 12,
    gap: 4,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 4,
    elevation: 2,
  },
  aiShortcutIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
  },
  aiShortcutTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#111827',
  },
  aiShortcutSub: {
    fontSize: 11,
    color: '#9CA3AF',
  },

  // AI card container
  aiCard: {
    marginTop: 20,
    backgroundColor: '#F8FAFC',
    borderRadius: 18,
    padding: 16,
    gap: 10,
  },
  aiHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  aiTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#111827',
  },

  // Vendor recommendation card
  vendorRecCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 12,
    gap: 10,
  },
  vendorRecIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  vendorRecContent: {
    flex: 1,
    gap: 1,
  },
  vendorRecName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
  },
  vendorRecReason: {
    fontSize: 12,
    color: '#2563EB',
    fontWeight: '600',
  },
  vendorRecRight: {
    alignItems: 'flex-end',
  },
  loadBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  loadBadgeText: {
    fontSize: 11,
    fontWeight: '700',
  },

  // Menu suggestion carousels
  recoRow: {
    paddingTop: 4,
    paddingBottom: 2,
  },
  recoCard: {
    width: 150,
    marginRight: 10,
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 10,
  },
  recoImage: {
    width: '100%',
    height: 80,
    borderRadius: 12,
    backgroundColor: '#F3F4F6',
  },
  recoImagePlaceholder: {
    width: '100%',
    height: 80,
    borderRadius: 12,
    backgroundColor: '#F3F4F6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  recoName: {
    marginTop: 6,
    fontSize: 13,
    fontWeight: '700',
    color: '#111827',
  },
  recoMeta: {
    marginTop: 2,
    fontSize: 11,
    color: '#6B7280',
  },
  recoReason: {
    marginTop: 3,
    fontSize: 11,
    color: '#0891B2',
  },
  recoReasonTrending: {
    marginTop: 3,
    fontSize: 11,
    color: '#D97706',
  },

  // Section variants
  frequentCard: {
    backgroundColor: '#F5F3FF',
  },
  frequentTitle: {
    color: '#6D28D9',
  },
  personalizedCard: {
    backgroundColor: '#F0FDFA',
  },
  personalizedTitle: {
    color: '#0E7490',
  },
  trendingCard: {
    backgroundColor: '#FFF7ED',
  },
  trendingTitle: {
    color: '#9A3412',
  },
  becauseCard: {
    backgroundColor: '#FDF2F8',
  },
  becauseTitle: {
    color: '#BE185D',
  },
  becauseReason: {
    color: '#DB2777',
  },

  // Popular Near You
  popularSection: {
    gap: 6,
  },
  popularLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: '#374151',
  },
  popularCard: {
    width: 130,
    marginRight: 10,
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 10,
    gap: 4,
    alignItems: 'center',
  },
  popularIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: '#D1FAE5',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
  },
  popularName: {
    fontSize: 13,
    fontWeight: '700',
    color: '#111827',
    textAlign: 'center',
  },
  popularStats: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  popularOrders: {
    fontSize: 11,
    color: '#6B7280',
  },
  popularRating: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  popularRatingText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#374151',
  },
});
