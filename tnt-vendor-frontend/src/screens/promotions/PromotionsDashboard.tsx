// ─── Promotions Dashboard ────────────────────────────────────────
// Premium marketing hub with campaigns, offers, and AI-driven recommendations

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../context/AuthContext';
import { retentionApi } from '../../services/retentionApi';
import { colors as staticColors, shadows, spacing } from '../../design-system';
const colors = staticColors;
import { formatRupees } from '../../utils/format';
import GlassCard from '../../design-system/components/GlassCard';
import StatCard from '../../design-system/components/StatCard';
import ForecastCard from '../../design-system/components/ForecastCard';
import AICard from '../../design-system/components/AICard';
import Badge from '../../design-system/components/Badge';
import { useTheme } from '../../context/ThemeContext';

type TabType = 'overview' | 'offers' | 'campaigns' | 'customers' | 'ai';

const segmentColors: Record<string, string> = {
  loyal: colors.success,
  repeat: colors.primary,
  new: colors.secondary,
  at_risk: colors.warning,
  lapsed: colors.error,
};

export default function PromotionsDashboard({ navigation }: any) {
  const { colors } = useTheme();
  const styles = getStyles(colors);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<any>(null);
  const [showCreateOffer, setShowCreateOffer] = useState(false);
  const [showCreateCampaign, setShowCreateCampaign] = useState(false);
  const { user } = useAuth();
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    loadData();
  }, []);

  const loadData = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      const [promoRes, offersRes, campaignsRes, customersRes, repeatRes, aiRes] = await Promise.all([
        retentionApi.getPromotions(),
        retentionApi.getOffers(),
        retentionApi.getCampaigns(),
        retentionApi.getCustomers(),
        retentionApi.getRepeatCustomers(),
        retentionApi.getAiSuggestions(),
      ]);
      setData({
        promotions: promoRes.data,
        offers: offersRes.data.offers || [],
        campaigns: campaignsRes.data.campaigns || [],
        customers: customersRes.data,
        repeat: repeatRes.data,
        ai: aiRes.data.suggestions || [],
      });
    } catch (err) {
      console.error('Promotions load error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '📊' },
    { key: 'offers', label: 'Offers', icon: '🎁' },
    { key: 'campaigns', label: 'Campaigns', icon: '📢' },
    { key: 'customers', label: 'Customers', icon: '👥' },
    { key: 'ai', label: 'AI', icon: '🤖' },
  ];

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading promotions...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Promotions</Text>
        <Text style={styles.headerSubtitle}>Grow & retain your customer base</Text>
      </View>

      {/* Tabs */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabRow} contentContainerStyle={styles.tabContentPad}>
        {tabs.map(tab => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, activeTab === tab.key && styles.tabActive]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Text style={styles.tabIcon}>{tab.icon}</Text>
            <Text style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]} numberOfLines={1}>{tab.label}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(true); }} tintColor={colors.primary} />}
        style={styles.scrollContent}
      >
        {/* Overview */}
        {activeTab === 'overview' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <View style={styles.statsRow}>
              <StatCard value={data?.promotions?.total_active || 0} label="Active Promotions" icon="🎯" color={colors.primary} style={{ flex: 1 }} />
              <StatCard value={data?.customers?.total_customers || 0} label="Total Customers" icon="👥" color={colors.secondary} style={{ flex: 1 }} />
            </View>
            <ForecastCard
              title="Retention Metrics"
              icon="🔄"
              color={colors.success}
              data={[
                { label: 'Repeat Rate', value: data?.repeat?.repeat_rate || 0, unit: '%', trend: (data?.repeat?.repeat_rate || 0) > 30 ? 'up' : 'down' },
                { label: 'Repeat Customers', value: data?.repeat?.total_repeat_customers || 0 },
                { label: 'Active Campaigns', value: data?.promotions?.active_campaigns?.length || 0 },
              ]}
              style={{ marginBottom: spacing.md }}
            />
            {data?.customers?.segments && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={styles.sectionTitle}>👥 Customer Segments</Text>
                {Object.entries(data.customers.segments).map(([segment, count]: any) => (
                  <View key={segment} style={styles.segmentRow}>
                    <View style={[styles.segmentDot, { backgroundColor: segmentColors[segment] || colors.textMuted }]} />
                    <Text style={styles.segmentName}>{segment.charAt(0).toUpperCase() + segment.slice(1)}</Text>
                    <Badge label={`${count}`} variant="primary" size="sm" />
                  </View>
                ))}
              </GlassCard>
            )}
            {(data?.ai || []).length > 0 && (
              <AICard
                icon="🤖"
                title="AI Suggestion Available"
                description={data.ai[0]?.title || 'New AI-driven promotion suggestion ready'}
                severity="info"
                action={{ label: 'View AI Suggestions', onPress: () => setActiveTab('ai') }}
                confidence={0.88}
              />
            )}
          </Animated.View>
        )}

        {/* Offers */}
        {activeTab === 'offers' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <TouchableOpacity style={styles.createButton} onPress={() => setShowCreateOffer(true)}>
              <Text style={styles.createButtonText}>+ Create New Offer</Text>
            </TouchableOpacity>
            {(data?.offers || []).length > 0 ? data.offers.map((offer: any, i: number) => (
              <GlassCard key={i} padding={16} borderRadius={18} style={{ marginBottom: spacing.sm }}>
                <View style={styles.offerHeader}>
                  <Text style={styles.offerTitle}>{offer.title}</Text>
                  <Badge label={offer.is_active ? 'Active' : 'Inactive'} variant={offer.is_active ? 'success' : 'neutral'} size="sm" />
                </View>
                <Text style={styles.offerType}>{offer.discount_type?.replace(/_/g, ' ')}</Text>
                <View style={styles.offerMeta}>
                  <Text style={styles.offerDiscount}>
                    {offer.discount_type === 'fixed' ? `${formatRupees(offer.discount_value)} OFF` : `${offer.discount_value}% OFF`}
                  </Text>
                  <Text style={styles.offerRedeemed}>{offer.times_redeemed} redeemed</Text>
                </View>
                {offer.is_dynamic && (
                  <Badge label={`AI Suggested • ${Math.round(offer.ai_confidence * 100)}% confidence`} variant="premium" size="sm" icon="🤖" />
                )}
              </GlassCard>
            )) : (
              <GlassCard padding={24} borderRadius={20}>
                <Text style={styles.emptyText}>No offers created yet.</Text>
              </GlassCard>
            )}
          </Animated.View>
        )}

        {/* Campaigns */}
        {activeTab === 'campaigns' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <TouchableOpacity style={styles.createButton} onPress={() => setShowCreateCampaign(true)}>
              <Text style={styles.createButtonText}>+ Create New Campaign</Text>
            </TouchableOpacity>
            {(data?.campaigns || []).length > 0 ? data.campaigns.map((campaign: any, i: number) => (
              <GlassCard key={i} padding={16} borderRadius={18} style={{ marginBottom: spacing.sm }}>
                <View style={styles.offerHeader}>
                  <Text style={styles.offerTitle}>{campaign.name}</Text>
                  <Badge label={campaign.status} variant={campaign.status === 'active' ? 'success' : campaign.status === 'draft' ? 'neutral' : 'warning'} size="sm" />
                </View>
                <Text style={styles.offerType}>{campaign.offer_type?.replace(/_/g, ' ')}</Text>
                <View style={styles.offerMeta}>
                  <Text style={styles.offerDiscount}>
                    {campaign.offer_type === 'discount_fixed' ? `${formatRupees(campaign.discount_value)} OFF` : `${campaign.discount_value}% OFF`}
                  </Text>
                  <Text style={styles.offerRedeemed}>{campaign.times_used} used</Text>
                </View>
                {campaign.is_combo && <Badge label="Combo Deal" variant="premium" size="sm" icon="📦" style={{ marginTop: 6 }} />}
                <Text style={styles.campaignDate}>
                  {campaign.start_date ? new Date(campaign.start_date).toLocaleDateString() : '—'} - {campaign.end_date ? new Date(campaign.end_date).toLocaleDateString() : '—'}
                </Text>
              </GlassCard>
            )) : (
              <GlassCard padding={24} borderRadius={20}>
                <Text style={styles.emptyText}>No campaigns running.</Text>
              </GlassCard>
            )}
          </Animated.View>
        )}

        {/* Customers */}
        {activeTab === 'customers' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
              <Text style={styles.sectionTitle}>⭐ Frequent Buyers</Text>
              {(data?.repeat?.frequent_buyers || []).slice(0, 5).map((c: any, i: number) => (
                <View key={i} style={styles.customerRow}>
                  <View style={styles.rankBadge}><Text style={styles.rankText}>#{i + 1}</Text></View>
                  <View style={styles.customerInfo}>
                    <Text style={styles.customerName}>{c.name}</Text>
                    <Text style={styles.customerMeta}>{c.total_orders} orders · {formatRupees(c.total_spent)}</Text>
                  </View>
                  <Badge label={c.segment} variant={c.segment === 'loyal' ? 'success' : c.segment === 'repeat' ? 'primary' : 'neutral'} size="sm" />
                </View>
              ))}
            </GlassCard>
          </Animated.View>
        )}

        {/* AI Suggestions */}
        {activeTab === 'ai' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <Text style={styles.sectionTitle}>🤖 AI Suggested Discounts</Text>
            {(data?.ai || []).length > 0 ? data.ai.map((s: any, i: number) => (
              <AICard
                key={i}
                icon={s.type === 'win_back' ? '🔄' : s.type === 'off_peak' ? '⏰' : s.type === 'combo' ? '📦' : '⭐'}
                title={s.title}
                description={s.description}
                severity="info"
                confidence={s.confidence || 0.85}
                style={{ marginBottom: spacing.sm }}
              />
            )) : (
              <GlassCard padding={24} borderRadius={20}>
                <Text style={styles.emptyText}>No AI suggestions yet. Data is being analyzed.</Text>
              </GlassCard>
            )}
          </Animated.View>
        )}
        <View style={{ height: spacing.huge }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const getStyles = (colors: any) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  tabRow: { height: 75, maxHeight: 75, marginTop: 8, marginBottom: 4 },
  tabContentPad: { paddingHorizontal: spacing.lg, gap: spacing.sm, paddingVertical: 12 },
  scrollContent: { flex: 1, paddingHorizontal: spacing.lg, paddingTop: 12, paddingBottom: 24 },
  tab: {
    flexDirection: 'row', alignItems: 'center', paddingHorizontal: 22, paddingVertical: 10,
    borderRadius: 14, backgroundColor: colors.bgCard, marginRight: 8, gap: 6,
    borderWidth: 1.5, borderColor: colors.border, ...shadows.sm,
  },
  tabActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  tabIcon: { fontSize: 14 },
  tabText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary },
  tabTextActive: { color: colors.textInverse },
  statsRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: 12 },
  segmentRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.borderLight, gap: 12 },
  segmentDot: { width: 10, height: 10, borderRadius: 5 },
  segmentName: { flex: 1, fontSize: 14, color: colors.textPrimary, fontWeight: '500' },
  createButton: { backgroundColor: colors.primary, borderRadius: 14, padding: 16, alignItems: 'center', marginBottom: spacing.md, ...shadows.button },
  createButtonText: { color: colors.textInverse, fontSize: 16, fontWeight: '700' },
  offerHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  offerTitle: { fontSize: 16, fontWeight: '600', color: colors.textPrimary, flex: 1 },
  offerType: { fontSize: 12, color: colors.textMuted, textTransform: 'capitalize', marginBottom: 6 },
  offerMeta: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  offerDiscount: { fontSize: 18, fontWeight: '700', color: colors.success },
  offerRedeemed: { fontSize: 13, color: colors.textSecondary },
  campaignDate: { fontSize: 12, color: colors.textMuted, marginTop: 6 },
  customerRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.borderLight, gap: 12 },
  rankBadge: { width: 28, height: 28, borderRadius: 14, backgroundColor: colors.warningPale, justifyContent: 'center', alignItems: 'center' },
  rankText: { fontSize: 12, fontWeight: '700', color: colors.warningDark },
  customerInfo: { flex: 1 },
  customerName: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  customerMeta: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  emptyText: { fontSize: 14, color: colors.textMuted, textAlign: 'center' },
});
