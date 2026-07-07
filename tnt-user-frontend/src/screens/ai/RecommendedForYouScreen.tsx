import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
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
import {
  getVendorRecommendations,
  getMenuSuggestions,
} from '../../services/recommendationService';
import type {
  VendorRecommendationItem,
  MenuSuggestionItem,
} from '../../services/recommendationService';
import { toAbsoluteUrl } from '../../utils/url';
import { formatMoneyPaise } from '../../utils/format';

type Props = NativeStackScreenProps<RootStackParamList, 'RecommendedForYou'>;

const VENDOR_TYPE_ICON: Record<string, { icon: string; color: string }> = {
  food: { icon: 'silverware-fork-knife', color: '#059669' },
  stationery: { icon: 'file-document-outline', color: '#2563EB' },
};

function LoadBadge({ level }: { level: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    LOW: { bg: '#D1FAE5', text: '#059669' },
    MEDIUM: { bg: '#FEF3C7', text: '#D97706' },
    HIGH: { bg: '#FEE2E2', text: '#DC2626' },
    CRITICAL: { bg: '#FEE2E2', text: '#991B1B' },
  };
  const c = config[level] ?? config.LOW;
  return (
    <View style={[styles.badge, { backgroundColor: c.bg }]}>
      <Text style={[styles.badgeText, { color: c.text }]}>{level}</Text>
    </View>
  );
}

export function RecommendedForYouScreen({ navigation }: Props) {
  const [vendors, setVendors] = useState<VendorRecommendationItem[]>([]);
  const [personalized, setPersonalized] = useState<MenuSuggestionItem[]>([]);
  const [trending, setTrending] = useState<MenuSuggestionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const [v, m] = await Promise.all([
        getVendorRecommendations(),
        getMenuSuggestions(),
      ]);
      setVendors(v.recommendations);
      setPersonalized(m.personalized);
      setTrending(m.trending);
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
          <Text style={styles.title}>Recommended For You</Text>
        </View>

        {/* Vendor Recommendations */}
        {vendors.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Top Vendors For You</Text>
            {vendors.map((v) => {
              const typeConf = VENDOR_TYPE_ICON[v.vendor_type] ?? VENDOR_TYPE_ICON.food;
              return (
                <Pressable
                  key={v.vendor_id}
                  style={styles.vendorCard}
                  onPress={() =>
                    navigation.navigate('Menu', {
                      vendorId: v.vendor_id,
                      vendorName: v.vendor_name,
                    })
                  }
                >
                  <View style={[styles.vendorIcon, { backgroundColor: typeConf.color + '15' }]}>
                    <MaterialCommunityIcons name={typeConf.icon as any} size={22} color={typeConf.color} />
                  </View>
                  <View style={styles.vendorContent}>
                    <Text style={styles.vendorName}>{v.vendor_name}</Text>
                    <Text style={styles.vendorReason}>{v.reason}</Text>
                    {v.category && (
                      <Text style={styles.vendorCategory}>{v.category}</Text>
                    )}
                  </View>
                  <View style={styles.vendorRight}>
                    <LoadBadge level={v.live_load} />
                    {v.express_pickup && (
                      <View style={styles.expressBadge}>
                        <MaterialCommunityIcons name="lightning-bolt" size={12} color="#D97706" />
                        <Text style={styles.expressText}>Express</Text>
                      </View>
                    )}
                  </View>
                </Pressable>
              );
            })}
          </View>
        )}

        {/* Personalized Menu Suggestions */}
        {personalized.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Picked For You</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.menuRow}>
              {personalized.map((item) => {
                const remoteUri = toAbsoluteUrl(item.image_url);
                const source = remoteUri ? { uri: remoteUri } : null;
                return (
                  <Pressable
                    key={`p-${item.item_id}`}
                    style={styles.menuCard}
                    onPress={() =>
                      navigation.navigate('Menu', {
                        vendorId: item.vendor_id,
                        vendorName: item.vendor_name,
                      })
                    }
                  >
                    {source ? (
                      <Image source={source} style={styles.menuImage} />
                    ) : (
                      <View style={styles.menuImagePlaceholder}>
                        <MaterialCommunityIcons name="food" size={24} color="#D1D5DB" />
                      </View>
                    )}
                    <Text style={styles.menuName} numberOfLines={1}>{item.item_name}</Text>
                    <Text style={styles.menuVendor} numberOfLines={1}>{item.vendor_name}</Text>
                    <Text style={styles.menuPrice}>{formatMoneyPaise(item.price_paise)}</Text>
                    <Text style={styles.menuReason} numberOfLines={1}>{item.reason}</Text>
                    <View style={styles.confidenceBar}>
                      <View style={[styles.confidenceFill, { width: `${item.confidence * 100}%` }]} />
                    </View>
                  </Pressable>
                );
              })}
            </ScrollView>
          </View>
        )}

        {/* Trending Items */}
        {trending.length > 0 && (
          <View style={styles.section}>
            <View style={styles.trendingHeader}>
              <MaterialCommunityIcons name="fire" size={18} color="#D97706" />
              <Text style={[styles.sectionTitle, styles.trendingTitle]}>Trending on Campus</Text>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.menuRow}>
              {trending.map((item) => {
                const remoteUri = toAbsoluteUrl(item.image_url);
                const source = remoteUri ? { uri: remoteUri } : null;
                return (
                  <Pressable
                    key={`t-${item.item_id}`}
                    style={styles.menuCard}
                    onPress={() =>
                      navigation.navigate('Menu', {
                        vendorId: item.vendor_id,
                        vendorName: item.vendor_name,
                      })
                    }
                  >
                    {source ? (
                      <Image source={source} style={styles.menuImage} />
                    ) : (
                      <View style={styles.menuImagePlaceholder}>
                        <MaterialCommunityIcons name="food" size={24} color="#D1D5DB" />
                      </View>
                    )}
                    <Text style={styles.menuName} numberOfLines={1}>{item.item_name}</Text>
                    <Text style={styles.menuVendor} numberOfLines={1}>{item.vendor_name}</Text>
                    <Text style={styles.menuPrice}>{formatMoneyPaise(item.price_paise)}</Text>
                    <Text style={styles.menuReason} numberOfLines={1}>{item.reason}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          </View>
        )}

        {vendors.length === 0 && personalized.length === 0 && trending.length === 0 && (
          <View style={styles.emptyState}>
            <MaterialCommunityIcons name="robot-outline" size={48} color="#D1D5DB" />
            <Text style={styles.emptyTitle}>No recommendations yet</Text>
            <Text style={styles.emptyText}>
              Place a few orders and we'll personalize suggestions for you!
            </Text>
          </View>
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: 32,
    gap: 16,
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
  section: {
    gap: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#111827',
    marginBottom: 4,
  },
  vendorCard: {
    flexDirection: 'row',
    alignItems: 'center',
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
  vendorIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  vendorContent: {
    flex: 1,
    gap: 2,
  },
  vendorName: {
    fontSize: 15,
    fontWeight: '700',
    color: '#111827',
  },
  vendorReason: {
    fontSize: 12,
    color: '#2563EB',
    fontWeight: '600',
  },
  vendorCategory: {
    fontSize: 11,
    color: '#9CA3AF',
  },
  vendorRight: {
    alignItems: 'flex-end',
    gap: 4,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  expressBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    backgroundColor: '#FEF3C7',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  expressText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#D97706',
  },
  menuRow: {
    paddingTop: 4,
    paddingBottom: 4,
  },
  menuCard: {
    width: 160,
    marginRight: 10,
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 10,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 4,
    elevation: 2,
  },
  menuImage: {
    width: '100%',
    height: 90,
    borderRadius: 12,
    backgroundColor: '#F3F4F6',
  },
  menuImagePlaceholder: {
    width: '100%',
    height: 90,
    borderRadius: 12,
    backgroundColor: '#F3F4F6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuName: {
    marginTop: 8,
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
  },
  menuVendor: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 1,
  },
  menuPrice: {
    fontSize: 14,
    fontWeight: '800',
    color: '#111827',
    marginTop: 2,
  },
  menuReason: {
    fontSize: 11,
    color: '#2563EB',
    marginTop: 2,
  },
  confidenceBar: {
    height: 3,
    borderRadius: 2,
    backgroundColor: '#E5E7EB',
    marginTop: 6,
    overflow: 'hidden',
  },
  confidenceFill: {
    height: '100%',
    borderRadius: 2,
    backgroundColor: '#3B82F6',
  },
  trendingHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  trendingTitle: {
    color: '#9A3412',
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
});
