// ─── AI Inventory Planning ────────────────────────────────────────
// Premium light-theme inventory intelligence with AI predictions

import React, { useCallback, useEffect, useState, useRef } from 'react';
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
import { vendorApi } from '../../services/vendorApi';
import { colors as staticColors, shadows, spacing } from '../../design-system';
const colors = staticColors;
import { formatRupees } from '../../utils/format';
import GlassCard from '../../design-system/components/GlassCard';
import StatCard from '../../design-system/components/StatCard';
import ForecastCard from '../../design-system/components/ForecastCard';
import AICard from '../../design-system/components/AICard';
import Badge from '../../design-system/components/Badge';
import { useTheme } from '../../context/ThemeContext';

type TabType = 'overview' | 'restock' | 'waste' | 'purchase';

export default function AIInventoryPlanningDashboard() {
  const { colors } = useTheme();
  const styles = getStyles(colors);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<any>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
  }, []);

  const loadPlan = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      setError(null);
      const response = await vendorApi.getAIInventoryPlan();
      setPlan(response.data);
    } catch (err: any) {
      setError(err?.message || 'Unable to load inventory plan');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { loadPlan(); }, [loadPlan]);

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '📊' },
    { key: 'restock', label: 'Restock', icon: '🔄' },
    { key: 'waste', label: 'Waste', icon: '♻️' },
    { key: 'purchase', label: 'Purchase', icon: '🛒' },
  ];

  const summary = plan?.summary || {};
  const insights = plan?.insights || [];

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.bg }, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={[styles.loadingText, { color: colors.textMuted }]}>Generating AI inventory plan...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.primary }]}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <Text style={[styles.headerTitle, { color: colors.textInverse }]}>Inventory AI</Text>
        <Text style={[styles.headerSubtitle, { color: 'rgba(255,255,255,0.7)' }]}>Smart predictions for optimal stock management</Text>
      </View>

      {/* Tabs */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabRow} contentContainerStyle={styles.tabContentPad}>
        {tabs.map(tab => (
          <TouchableOpacity
            key={tab.key}
            style={[
              styles.tab,
              { backgroundColor: colors.bgCard, borderColor: colors.border },
              activeTab === tab.key && [styles.tabActive, { backgroundColor: colors.primary, borderColor: colors.primary }]
            ]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Text style={styles.tabIcon}>{tab.icon}</Text>
            <Text style={[
              styles.tabText,
              { color: colors.textSecondary },
              activeTab === tab.key && [styles.tabTextActive, { color: colors.textInverse }]
            ]} numberOfLines={1}>{tab.label}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={() => loadPlan()}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadPlan(true); }} tintColor={colors.primary} />}
        style={styles.scrollContent}
      >
        {/* Summary Cards */}
        <View style={styles.statsRow}>
          <StatCard value={summary.total_items || 0} label="Total Items" icon="📦" color={colors.primary} size="sm" style={{ flexBasis: '30%', flexGrow: 1 }} />
          <StatCard value={summary.low_stock || 0} label="Low Stock" icon="⚠️" color={(summary.low_stock || 0) > 0 ? colors.warning : colors.success} size="sm" style={{ flexBasis: '30%', flexGrow: 1 }} />
          <StatCard value={summary.out_of_stock || 0} label="Out of Stock" icon="🚫" color={(summary.out_of_stock || 0) > 0 ? colors.error : colors.success} size="sm" style={{ flexBasis: '30%', flexGrow: 1 }} />
        </View>
        <View style={styles.statsRow}>
          <StatCard value={summary.items_with_waste_risk || 0} label="Waste Risk" icon="♻️" color={(summary.items_with_waste_risk || 0) > 0 ? colors.warning : colors.success} size="sm" style={{ flexBasis: '30%', flexGrow: 1 }} />
          <StatCard value={summary.items_to_restock || 0} label="To Restock" icon="🔄" color={(summary.items_to_restock || 0) > 0 ? colors.info : colors.success} size="sm" style={{ flexBasis: '30%', flexGrow: 1 }} />
          <StatCard value={summary.items_likely_to_finish || 0} label="At Risk" icon="⏰" color={(summary.items_likely_to_finish || 0) > 0 ? colors.error : colors.success} size="sm" style={{ flexBasis: '30%', flexGrow: 1 }} />
        </View>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            {/* Items Likely to Finish */}
            {(plan?.items_likely_to_finish || []).length > 0 && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>⏰ Items Likely to Finish</Text>
                {plan.items_likely_to_finish.slice(0, 5).map((item: any, i: number) => (
                  <View key={i} style={[styles.itemRow, { borderBottomColor: colors.borderLight }]}>
                    <View style={styles.itemInfo}>
                      <Text style={[styles.itemName, { color: colors.textPrimary }]}>{item.item_name}</Text>
                      <Text style={[styles.itemDetail, { color: colors.textSecondary }]}>Stock: {item.current_stock} | Demand: {item.daily_demand}/day</Text>
                    </View>
                    <View style={styles.itemRight}>
                      <Badge
                        label={item.severity}
                        variant={item.severity === 'critical' ? 'error' : item.severity === 'high' ? 'warning' : 'info'}
                        size="sm"
                      />
                      <Text style={[styles.daysLeft, { color: item.days_until_out <= 2 ? colors.error : colors.warning }]}>
                        {item.days_until_out}d left
                      </Text>
                    </View>
                  </View>
                ))}
              </GlassCard>
            )}

            {/* Insights */}
            {insights.length > 0 && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>💡 AI Insights</Text>
                {insights.map((insight: string, i: number) => (
                  <View key={i} style={styles.insightRow}>
                    <Text style={[styles.bullet, { color: colors.primary }]}>•</Text>
                    <Text style={[styles.insightText, { color: colors.textSecondary }]}>{insight}</Text>
                  </View>
                ))}
              </GlassCard>
            )}

            {/* Demand */}
            {plan?.expected_demand?.items && (
              <ForecastCard
                title="Expected Demand"
                icon="📊"
                color={colors.primary}
                data={(plan.expected_demand.items || []).slice(0, 5).map((d: any) => ({
                  label: d.item_name,
                  value: d.daily || 0,
                  unit: '/day',
                }))}
                style={{ marginBottom: spacing.md }}
              />
            )}
          </Animated.View>
        )}

        {/* Restock Tab */}
        {activeTab === 'restock' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Restock Suggestions</Text>
            {(plan?.restock_suggestions || []).length > 0 ? (
              plan.restock_suggestions.map((s: any, i: number) => (
                <GlassCard key={i} padding={16} borderRadius={18} style={{ marginBottom: spacing.sm }}>
                  <View style={styles.suggestionHeader}>
                    <Text style={[styles.suggestionName, { color: colors.textPrimary }]}>{s.item_name}</Text>
                    <Badge label={s.priority} variant={s.priority === 'critical' ? 'error' : s.priority === 'high' ? 'warning' : 'info'} size="sm" />
                  </View>
                  <View style={styles.suggestionDetails}>
                    <Text style={[styles.suggestionDetail, { color: colors.textSecondary }]}>Current Stock: {s.current_stock}</Text>
                    <Text style={[styles.suggestionDetail, { color: colors.textSecondary }]}>Suggested: {s.suggested_quantity} units</Text>
                    {s.restock_by && <Text style={[styles.suggestionDetail, { color: colors.textSecondary }]}>Restock By: {s.restock_by}</Text>}
                  </View>
                  <Text style={[styles.suggestionReason, { color: colors.warningDark }]}>{s.reason}</Text>
                </GlassCard>
              ))
            ) : (
              <GlassCard padding={24} borderRadius={20}>
                <Text style={[styles.emptyText, { color: colors.textMuted }]}>All items adequately stocked — no restock suggestions.</Text>
              </GlassCard>
            )}
          </Animated.View>
        )}

        {/* Waste Tab */}
        {activeTab === 'waste' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Waste Reduction</Text>
            {(plan?.waste_reduction_suggestions || []).length > 0 ? (
              plan.waste_reduction_suggestions.map((s: any, i: number) => (
                <AICard
                  key={i}
                  icon="♻️"
                  title={s.type?.replace(/_/g, ' ').toUpperCase()}
                  description={s.suggestion}
                  severity={s.severity === 'high' ? 'warning' : s.severity === 'medium' ? 'info' : 'success'}
                  confidence={0.85}
                  style={{ marginBottom: spacing.sm }}
                />
              ))
            ) : (
              <GlassCard padding={24} borderRadius={20}>
                <Text style={[styles.emptyText, { color: colors.textMuted }]}>No waste reduction suggestions available.</Text>
              </GlassCard>
            )}
          </Animated.View>
        )}

        {/* Purchase Tab */}
        {activeTab === 'purchase' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            {plan?.total_estimated_cost > 0 && (
              <GlassCard padding={20} borderRadius={20} style={{ marginBottom: spacing.md, alignItems: 'center' }}>
                <Text style={[styles.totalCostLabel, { color: colors.textMuted }]}>Estimated Total Cost</Text>
                <Text style={[styles.totalCostValue, { color: colors.success }]}>{formatRupees(plan.total_estimated_cost)}</Text>
              </GlassCard>
            )}
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Smart Purchase Plan</Text>
            {(plan?.smart_purchase_plan || []).length > 0 ? (
              plan.smart_purchase_plan.map((item: any, i: number) => (
                <GlassCard key={i} padding={16} borderRadius={18} style={{ marginBottom: spacing.sm }}>
                  <View style={styles.suggestionHeader}>
                    <Text style={[styles.suggestionName, { color: colors.textPrimary }]}>{item.item_name}</Text>
                    <Badge label={item.priority} variant={item.priority === 'critical' ? 'error' : item.priority === 'high' ? 'warning' : 'info'} size="sm" />
                  </View>
                  <View style={styles.purchaseDetails}>
                    {[
                      ['Current Stock', item.current_stock],
                      ['Daily Demand', item.daily_demand],
                      ['Optimal Qty', item.optimal_quantity],
                      ['Days to Cover', `${item.days_to_cover}d`],
                      ['Delivery Window', item.expected_delivery_window],
                    ].map(([label, value], idx) => (
                      <View key={idx} style={[styles.purchaseRow, { borderBottomColor: colors.borderLight }]}>
                        <Text style={[styles.purchaseLabel, { color: colors.textSecondary }]}>{label}</Text>
                        <Text style={[styles.purchaseValue, { color: colors.textPrimary }, label === 'Optimal Qty' && { color: colors.success, fontWeight: '700' }]}>{value}</Text>
                      </View>
                    ))}
                  </View>
                  {item.suggested_vendor && (
                    <Text style={[styles.vendorText, { color: colors.info }]}>🏪 {item.suggested_vendor}</Text>
                  )}
                </GlassCard>
              ))
            ) : (
              <GlassCard padding={24} borderRadius={20}>
                <Text style={[styles.emptyText, { color: colors.textMuted }]}>No purchase plan available.</Text>
              </GlassCard>
            )}
          </Animated.View>
        )}
        <View style={{ height: 100 }} />
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
  statsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginBottom: spacing.md },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: 12 },
  errorBox: { margin: spacing.md, padding: 16, backgroundColor: colors.errorPale, borderRadius: 14, borderWidth: 1, borderColor: colors.error + '30', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  errorText: { color: colors.error, fontSize: 14, flex: 1 },
  retryText: { color: colors.primary, fontSize: 14, fontWeight: '700', marginLeft: 12 },
  itemRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.borderLight },
  itemInfo: { flex: 1 },
  itemName: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  itemDetail: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  itemRight: { alignItems: 'flex-end', gap: 4 },
  daysLeft: { fontSize: 12, fontWeight: '700' },
  insightRow: { flexDirection: 'row', marginBottom: 6, gap: 6 },
  bullet: { color: colors.primary, fontSize: 16 },
  insightText: { flex: 1, fontSize: 13, color: colors.textSecondary, lineHeight: 18 },
  suggestionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  suggestionName: { fontSize: 16, fontWeight: '600', color: colors.textPrimary, flex: 1 },
  suggestionDetails: { marginBottom: 8, gap: 4 },
  suggestionDetail: { fontSize: 13, color: colors.textSecondary },
  suggestionReason: { fontSize: 12, color: colors.warningDark, fontWeight: '500' },
  totalCostLabel: { fontSize: 14, color: colors.textMuted, marginBottom: 4 },
  totalCostValue: { fontSize: 32, fontWeight: '700', color: colors.success },
  purchaseDetails: { gap: 2, marginBottom: 8 },
  purchaseRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: colors.borderLight },
  purchaseLabel: { fontSize: 13, color: colors.textSecondary },
  purchaseValue: { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  vendorText: { fontSize: 12, color: colors.info, fontWeight: '600' },
  emptyText: { fontSize: 14, color: colors.textMuted, textAlign: 'center' },
});
