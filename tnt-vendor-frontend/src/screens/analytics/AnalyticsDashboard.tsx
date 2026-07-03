// ─── Analytics Dashboard ──────────────────────────────────────────
// Premium interactive analytics with revenue charts, trends, heatmaps

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
import { useAuth } from '../../context/AuthContext';
import { analyticsApi } from '../../services/analyticsApi';
import { vendorApi } from '../../services/vendorApi';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatCard from '../../design-system/components/StatCard';
import ForecastCard from '../../design-system/components/ForecastCard';
import RevenueCard from '../../design-system/components/RevenueCard';
import AICard from '../../design-system/components/AICard';

type TabType = 'revenue' | 'orders' | 'items' | 'peak' | 'waste' | 'stationery';

export default function AnalyticsDashboard({ navigation }: any) {
  const [activeTab, setActiveTab] = useState<TabType>('revenue');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<any>(null);
  const [stationeryData, setStationeryData] = useState<any>(null);
  const { user } = useAuth();

  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    loadData();
  }, []);

  const loadData = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      const [dailyRes, weeklyRes, itemsRes, peakRes, wasteRes] = await Promise.all([
        analyticsApi.getDailySales(),
        analyticsApi.getWeeklySales(),
        analyticsApi.getItemAnalysis(),
        analyticsApi.getPeakHours(),
        analyticsApi.getWasteAnalysis(),
      ]);
      setData({
        daily: dailyRes.data,
        weekly: weeklyRes.data,
        items: itemsRes.data,
        peak: peakRes.data,
        waste: wasteRes.data,
      });
      // Load stationery forecast in background (non-blocking)
      try {
        const stRes = await vendorApi.getForecastByType();
        setStationeryData((stRes as any).data);
      } catch {
        // Not a stationery vendor — stationeryData stays null
      }
    } catch (err) {
      console.error('Analytics load error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'revenue', label: 'Revenue', icon: '💰' },
    { key: 'orders', label: 'Orders', icon: '📦' },
    { key: 'items', label: 'Items', icon: '🔥' },
    { key: 'peak', label: 'Peak Hours', icon: '⏰' },
    { key: 'waste', label: 'Waste', icon: '♻️' },
    { key: 'stationery', label: 'Print Jobs', icon: '🖨️' },
  ];

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading analytics...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Analytics</Text>
        <Text style={styles.headerSubtitle}>Data-driven insights for {user?.vendor_name}</Text>
      </View>

      {/* Tabs */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabRow} contentContainerStyle={styles.tabContent}>
        {tabs.map(tab => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, activeTab === tab.key && styles.tabActive]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Text style={styles.tabIcon}>{tab.icon}</Text>
            <Text style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]}>{tab.label}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(true); }} tintColor={colors.primary} />}
        style={styles.tabContent}
      >
        {/* Revenue Tab */}
        {activeTab === 'revenue' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <RevenueCard
              title="Today's Revenue"
              amount={data?.daily?.total_revenue || 0}
              subtitle="Last 7 days performance"
              trend={{ value: data?.weekly?.growth_percentage || 0, isUp: (data?.weekly?.growth_percentage || 0) >= 0 }}
              data={(data?.daily?.sales_data || []).slice(-7).map((d: any) => ({
                value: d.revenue,
                label: new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' }).charAt(0),
              }))}
              color={colors.primary}
              style={{ marginBottom: spacing.md }}
            />
            <ForecastCard
              title="Revenue Forecast"
              icon="📈"
              color={colors.success}
              data={[
                { label: 'Daily Avg', value: data?.daily?.daily_average_revenue || 0, unit: '₹' },
                { label: 'Weekly Avg', value: data?.weekly?.weekly_average_revenue || 0, unit: '₹' },
                { label: 'Weekly Growth', value: Math.abs(data?.weekly?.growth_percentage || 0), unit: '%', trend: (data?.weekly?.growth_percentage || 0) >= 0 ? 'up' : 'down' },
              ]}
              style={{ marginBottom: spacing.md }}
            />
            {data?.daily?.sales_data && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={styles.sectionTitle}>Sales Breakdown</Text>
                {data.daily.sales_data.slice(-7).reverse().map((day: any, i: number) => (
                  <View key={i} style={styles.dataRow}>
                    <Text style={styles.dataLabel}>
                      {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                    </Text>
                    <Text style={styles.dataValue}>{day.orders} orders</Text>
                    <Text style={[styles.dataAmount, { color: colors.primary }]}>₹{day.revenue}</Text>
                  </View>
                ))}
              </GlassCard>
            )}
          </Animated.View>
        )}

        {/* Orders Tab */}
        {activeTab === 'orders' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <View style={styles.statsRow}>
              <StatCard value={data?.daily?.total_orders || 0} label="Today" icon="📦" color={colors.primary} style={{ flex: 1 }} />
              <StatCard value={data?.weekly?.total_orders || 0} label="This Week" icon="📊" color={colors.secondary} style={{ flex: 1 }} />
            </View>
            <ForecastCard
              title="Orders Overview"
              icon="📋"
              color={colors.info}
              data={[
                { label: 'Total Orders', value: data?.daily?.total_orders || 0 },
                { label: 'Daily Avg', value: data?.daily?.daily_average_orders || Math.round((data?.daily?.total_orders || 0) / 30) || 0 },
                { label: 'Growth Trend', value: Math.abs(data?.weekly?.growth_percentage || 0), unit: '%', trend: (data?.weekly?.growth_percentage || 0) >= 0 ? 'up' : 'down' },
              ]}
              style={{ marginBottom: spacing.md }}
            />
            {data?.daily?.sales_data && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={styles.sectionTitle}>Order Trends</Text>
                <View style={styles.chartContainer}>
                  {data.daily.sales_data.slice(-10).map((day: any, i: number) => {
                    const maxOrders = Math.max(...data.daily.sales_data.slice(-10).map((d: any) => d.orders), 1);
                    const height = (day.orders / maxOrders) * 80;
                    return (
                      <View key={i} style={styles.barCol}>
                        <View style={[styles.bar, { height: Math.max(height, 4), backgroundColor: i === 9 ? colors.primary : `${colors.primary}60` }]} />
                        <Text style={styles.barLabel}>{new Date(day.date).getDate()}</Text>
                      </View>
                    );
                  })}
                </View>
              </GlassCard>
            )}
          </Animated.View>
        )}

        {/* Items Tab */}
        {activeTab === 'items' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
              <Text style={styles.sectionTitle}>🔥 Popular Items</Text>
              <Text style={styles.sectionSubtitle}>Top selling items by order count</Text>
              {(data?.items?.popular_items || []).map((item: any, i: number) => (
                <View key={i} style={styles.itemRow}>
                  <View style={styles.rankCircle}>
                    <Text style={styles.rankText}>#{i + 1}</Text>
                  </View>
                  <View style={styles.itemInfo}>
                    <Text style={styles.itemName}>{item.name}</Text>
                    <Text style={styles.itemStats}>{item.order_count} orders · {item.total_quantity} units</Text>
                  </View>
                  <Text style={styles.itemRevenue}>₹{item.total_revenue}</Text>
                </View>
              ))}
            </GlassCard>
            {(data?.items?.low_selling_items || []).length > 0 && (
              <AICard
                icon="📉"
                title="Low Performing Items"
                description={`${data.items.low_selling_items.length} items need attention`}
                severity="warning"
                action={{ label: 'Review Menu', onPress: () => navigation.navigate('Menu') }}
                confidence={0.88}
              />
            )}
          </Animated.View>
        )}

        {/* Peak Hours Tab */}
        {activeTab === 'peak' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <ForecastCard
              title="Peak Hour Distribution"
              icon="⏰"
              color={colors.warning}
              data={(data?.peak?.hourly_distribution || []).filter((_: any, i: number) => i % 2 === 0).map((h: any) => ({
                label: h.hour,
                value: h.orders,
                unit: 'orders',
              }))}
              style={{ marginBottom: spacing.md }}
            />
            {(data?.peak?.peak_periods || []).length > 0 && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={styles.sectionTitle}>🔴 Peak Periods</Text>
                {data.peak.peak_periods.map((period: any, i: number) => (
                  <View key={i} style={styles.peakRow}>
                    <Text style={styles.peakLabel}>{period.label}</Text>
                    <View style={[styles.peakBar, { width: `${Math.min(100, period.orders * 5)}%` }]}>
                      <Text style={styles.peakCount}>{period.orders} orders</Text>
                    </View>
                  </View>
                ))}
              </GlassCard>
            )}
          </Animated.View>
        )}

        {/* Waste Tab */}
        {activeTab === 'waste' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <View style={styles.statsRow}>
              <StatCard value={data?.waste?.cancellation_rate || 0} label="Cancellation Rate" suffix="%" color={colors.error} style={{ flex: 1 }} />
              <StatCard value={data?.waste?.wasted_revenue || 0} label="Wasted Revenue" prefix="₹" color={colors.warning} style={{ flex: 1 }} format="currency" />
            </View>
            <ForecastCard
              title="Waste Analysis"
              icon="♻️"
              color={colors.error}
              data={[
                { label: 'Cancelled Orders', value: data?.waste?.cancelled_orders || 0 },
                { label: 'Daily Waste Avg', value: data?.waste?.daily_waste_average || 0, unit: '₹' },
                { label: 'Cancellation Rate', value: data?.waste?.cancellation_rate || 0, unit: '%', trend: (data?.waste?.cancellation_rate || 0) > 10 ? 'up' : 'down' },
              ]}
              style={{ marginBottom: spacing.md }}
            />
            {(data?.waste?.wasted_items || []).length > 0 && (
              <AICard
                icon="🗑️"
                title="Waste Reduction Opportunity"
                description={`${data.waste.wasted_items.length} items frequently cancelled. Consider portion adjustments.`}
                severity="warning"
                action={{ label: 'View Details', onPress: () => {} }}
                confidence={0.85}
              />
            )}
          </Animated.View>
        )}
        {/* Stationery / Print-Jobs Tab */}
        {activeTab === 'stationery' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            {stationeryData?.stationery_breakdown ? (
              <>
                <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                  <Text style={styles.sectionTitle}>🖨️ Print Job Breakdown</Text>
                  <Text style={styles.sectionSubtitle}>Last 30 days by service type</Text>
                  {[
                    { label: 'Print Jobs', value: stationeryData.stationery_breakdown.print_jobs, icon: '🖨️', color: colors.primary },
                    { label: 'Xerox / Copy', value: stationeryData.stationery_breakdown.xerox_jobs, icon: '📋', color: colors.secondary },
                    { label: 'Binding', value: stationeryData.stationery_breakdown.binding_jobs, icon: '📚', color: colors.info },
                    { label: 'Total Jobs', value: stationeryData.stationery_breakdown.total_jobs, icon: '📊', color: colors.success },
                  ].map((row, i) => (
                    <View key={i} style={styles.dataRow}>
                      <Text style={styles.dataLabel}>{row.icon}  {row.label}</Text>
                      <Text style={[styles.dataAmount, { color: row.color }]}>{row.value}</Text>
                    </View>
                  ))}
                </GlassCard>

                {/* Load vs capacity using peak data */}
                {data?.peak?.hourly_distribution && (
                  <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                    <Text style={styles.sectionTitle}>⏱ Busiest Print Windows</Text>
                    <Text style={styles.sectionSubtitle}>Peak order hours (proxy for print load)</Text>
                    <View style={styles.chartContainer}>
                      {data.peak.hourly_distribution
                        .filter((_: any, i: number) => i >= 8 && i <= 20)
                        .map((h: any, i: number) => {
                          const maxOrders = Math.max(...data.peak.hourly_distribution.map((d: any) => d.orders), 1);
                          const height = (h.orders / maxOrders) * 80;
                          return (
                            <View key={i} style={styles.barCol}>
                              <View style={[styles.bar, { height: Math.max(height, 4), backgroundColor: h.is_peak ? colors.primary : `${colors.primary}40` }]} />
                              <Text style={styles.barLabel}>{h.hour.split(':')[0]}</Text>
                            </View>
                          );
                        })}
                    </View>
                    {data.peak.busiest_hour && (
                      <Text style={{ fontSize: 12, color: colors.textMuted, marginTop: 8 }}>
                        🏆 Busiest hour: <Text style={{ color: colors.primary, fontWeight: '700' }}>{data.peak.busiest_hour}</Text>
                      </Text>
                    )}
                  </GlassCard>
                )}

                {/* Forecast summary */}
                {stationeryData?.daily?.summary && (
                  <ForecastCard
                    title="Stationery Demand Forecast"
                    icon="📈"
                    color={colors.info}
                    data={[
                      { label: 'Predicted Orders (7d)', value: stationeryData.daily.summary.total_orders || 0 },
                      { label: 'Avg Daily Revenue', value: stationeryData.daily.summary.avg_daily_revenue || 0, unit: '₹' },
                    ]}
                    style={{ marginBottom: spacing.md }}
                  />
                )}
              </>
            ) : (
              <GlassCard padding={24} borderRadius={20} style={{ margin: spacing.lg, alignItems: 'center' }}>
                <Text style={{ fontSize: 40, marginBottom: 12 }}>🖨️</Text>
                <Text style={[styles.sectionTitle, { textAlign: 'center' }]}>Stationery Analytics</Text>
                <Text style={[styles.sectionSubtitle, { textAlign: 'center' }]}>
                  Not available — this vendor is not classified as a stationery vendor,
                  or no stationery orders have been placed yet.
                </Text>
              </GlassCard>
            )}
          </Animated.View>
        )}

        <View style={{ height: spacing.huge }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.huge + 20,
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
  tabRow: { maxHeight: 52 },
  tabContent: { paddingHorizontal: spacing.lg, gap: spacing.sm, paddingVertical: spacing.md },
  tab: {
    flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10,
    borderRadius: 14, backgroundColor: colors.bgCard, marginRight: 8, gap: 6,
    borderWidth: 1.5, borderColor: colors.border, ...shadows.sm,
  },
  tabActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  tabIcon: { fontSize: 14 },
  tabText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary },
  tabTextActive: { color: colors.textInverse },
  statsRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 },
  sectionSubtitle: { fontSize: 12, color: colors.textMuted, marginBottom: spacing.md },
  chartContainer: { flexDirection: 'row', alignItems: 'flex-end', height: 100, gap: 4, paddingTop: spacing.md },
  barCol: { flex: 1, alignItems: 'center' },
  bar: { width: '70%', borderRadius: 6, minHeight: 4 },
  barLabel: { fontSize: 10, color: colors.textMuted, fontWeight: '600', marginTop: 4 },
  dataRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.borderLight },
  dataLabel: { flex: 1, fontSize: 13, color: colors.textSecondary },
  dataValue: { fontSize: 13, color: colors.textMuted, marginRight: 12 },
  dataAmount: { fontSize: 14, fontWeight: '700' },
  itemRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.borderLight },
  rankCircle: { width: 28, height: 28, borderRadius: 14, backgroundColor: colors.warningPale, justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  rankText: { fontSize: 12, fontWeight: '700', color: colors.warningDark },
  itemInfo: { flex: 1 },
  itemName: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  itemStats: { fontSize: 11, color: colors.textMuted, marginTop: 2 },
  itemRevenue: { fontSize: 14, fontWeight: '700', color: colors.success },
  peakRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 8 },
  peakLabel: { fontSize: 13, fontWeight: '600', color: colors.textSecondary, width: 60 },
  peakBar: { height: 24, backgroundColor: colors.warning, borderRadius: 6, justifyContent: 'center', paddingHorizontal: 8 },
  peakCount: { color: colors.textInverse, fontSize: 11, fontWeight: '600' },
});
