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
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../context/AuthContext';
import { analyticsApi } from '../../services/analyticsApi';
import { vendorApi } from '../../services/vendorApi';
import { colors as staticColors, shadows, spacing } from '../../design-system';
const colors = staticColors;
import { formatRupees } from '../../utils/format';
import GlassCard from '../../design-system/components/GlassCard';
import StatCard from '../../design-system/components/StatCard';
import ForecastCard from '../../design-system/components/ForecastCard';
import RevenueCard from '../../design-system/components/RevenueCard';
import AICard from '../../design-system/components/AICard';
import { useTheme } from '../../context/ThemeContext';

type TabType = 'revenue' | 'orders' | 'items' | 'peak' | 'waste' | 'yearly' | 'stationery' | 'heatmap';

export default function AnalyticsDashboard({ navigation }: any) {
  const { colors } = useTheme();
  const styles = getStyles(colors);
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
      const [dailyRes, weeklyRes, itemsRes, peakRes, wasteRes, yearlyRes] = await Promise.all([
        analyticsApi.getDailySales(),
        analyticsApi.getWeeklySales(),
        analyticsApi.getItemAnalysis(),
        analyticsApi.getPeakHours(),
        analyticsApi.getWasteAnalysis(),
        analyticsApi.getYearlySales(),
      ]);
      setData({
        daily: dailyRes.data,
        weekly: weeklyRes.data,
        items: itemsRes.data,
        peak: peakRes.data,
        waste: wasteRes.data,
        yearly: yearlyRes.data,
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
    { key: 'yearly', label: 'Yearly', icon: '📅' },
    { key: 'stationery', label: 'Print Jobs', icon: '🖨️' },
    { key: 'heatmap', label: 'Heatmap', icon: '🗺️' },
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
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
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
        style={styles.scrollContent}
      >
        {/* Revenue Tab */}
        {activeTab === 'revenue' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <RevenueCard
              title="Today's Revenue"
              amount={(data?.daily?.total_revenue || 0)}
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
                { label: 'Daily Avg', value: (data?.daily?.daily_average_revenue || 0), unit: '₹' },
                { label: 'Weekly Avg', value: (data?.weekly?.weekly_average_revenue || 0), unit: '₹' },
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
                    <Text style={[styles.dataAmount, { color: colors.primary }]}>{formatRupees(day.revenue)}</Text>
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
                  <Text style={styles.itemRevenue}>{formatRupees(item.total_revenue)}</Text>
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
              <StatCard value={(data?.waste?.wasted_revenue || 0)} label="Wasted Revenue" prefix="₹" color={colors.warning} style={{ flex: 1 }} format="currency" />
            </View>
            <ForecastCard
              title="Waste Analysis"
              icon="♻️"
              color={colors.error}
              data={[
                { label: 'Cancelled Orders', value: data?.waste?.cancelled_orders || 0 },
                { label: 'Daily Waste Avg', value: (data?.waste?.daily_waste_average || 0), unit: '₹' },
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
        {/* Yearly Tab */}
        {activeTab === 'yearly' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <View style={styles.statsRow}>
              <StatCard value={(data?.yearly?.yearly_total_revenue || data?.yearly?.total_revenue || 0)} label="Yearly Revenue" prefix="₹" color={colors.primary} style={{ flex: 1 }} format="currency" />
              <StatCard value={data?.yearly?.yearly_total_orders || data?.yearly?.total_orders || 0} label="Total Orders" icon="📦" color={colors.secondary} style={{ flex: 1 }} />
            </View>
            <ForecastCard
              title="Yearly Performance"
              icon="📅"
              color={colors.primary}
              data={[
                { label: 'Yearly Revenue', value: (data?.yearly?.yearly_total_revenue || data?.yearly?.total_revenue || 0), unit: '₹' },
                { label: 'Yearly Orders', value: data?.yearly?.yearly_total_orders || data?.yearly?.total_orders || 0 },
                { label: 'Monthly Avg', value: (data?.yearly?.monthly_average || data?.yearly?.avg_monthly_revenue || 0), unit: '₹' },
                { label: 'Growth vs Prev Year', value: Math.abs(data?.yearly?.growth_percentage || 0), unit: '%', trend: (data?.yearly?.growth_percentage || 0) >= 0 ? 'up' : 'down' },
              ]}
              style={{ marginBottom: spacing.md }}
            />
            {data?.yearly?.monthly_data && data.yearly.monthly_data.length > 0 && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={styles.sectionTitle}>📊 Monthly Breakdown</Text>
                <View style={styles.chartContainer}>
                  {data.yearly.monthly_data.map((month: any, i: number) => {
                    const maxVal = Math.max(...data.yearly.monthly_data.map((m: any) => m.revenue || m.total || 0), 1);
                    const height = ((month.revenue || month.total || 0) / maxVal) * 80;
                    return (
                      <View key={i} style={styles.barCol}>
                        <View style={[styles.bar, { height: Math.max(height, 4), backgroundColor: i === data.yearly.monthly_data.length - 1 ? colors.primary : `${colors.primary}60` }]} />
                        <Text style={styles.barLabel}>{month.month?.slice(0, 3) || i + 1}</Text>
                      </View>
                    );
                  })}
                </View>
              </GlassCard>
            )}
            <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
              <Text style={styles.sectionTitle}>📈 Key Insights</Text>
              <View style={styles.insightsList}>
                <View style={styles.insightRow}>
                  <Text style={styles.insightDot}>•</Text>
                  <Text style={styles.insightText}>
                    Best month: <Text style={{ fontWeight: '700' }}>{data?.yearly?.best_month || 'N/A'}</Text>
                  </Text>
                </View>
                <View style={styles.insightRow}>
                  <Text style={styles.insightDot}>•</Text>
                  <Text style={styles.insightText}>
                    Monthly avg: <Text style={{ fontWeight: '700' }}>₹{((data?.yearly?.monthly_average || data?.yearly?.avg_monthly_revenue || 0)).toFixed(2)}</Text>
                  </Text>
                </View>
              </View>
            </GlassCard>
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
                      { label: 'Avg Daily Revenue', value: (stationeryData.daily.summary.avg_daily_revenue || 0), unit: '₹' },
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

        {/* Heatmap Tab — Slot Congestion Visualization */}
        {activeTab === 'heatmap' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <View style={styles.statsRow}>
              <StatCard value={data?.peak?.total_orders || data?.daily?.total_orders || 0} label="Orders Analyzed" icon="📊" color={colors.primary} style={{ flex: 1 }} />
              <StatCard value={data?.peak?.peak_periods?.length || 0} label="Congested Windows" icon="🔴" color={colors.error} style={{ flex: 1 }} />
            </View>

            {/* Hourly Congestion Grid — Heatmap style */}
            <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
              <Text style={styles.sectionTitle}>🔥 Slot Congestion Heatmap</Text>
              <Text style={styles.sectionSubtitle}>Hourly order density — darker = higher congestion</Text>
              <View style={styles.heatmapGrid}>
                {(() => {
                  const hours = (data?.peak?.hourly_distribution || []).filter((_: any, i: number) => i >= 7 && i <= 22);
                  const maxOrders = Math.max(...hours.map((h: any) => h.orders), 1);
                  return hours.map((h: any, i: number) => {
                    const intensity = h.orders / maxOrders;
                    const bgColor = intensity > 0.75 ? colors.error
                      : intensity > 0.5 ? colors.warning
                      : intensity > 0.25 ? colors.info + '80'
                      : colors.success + '60';
                    return (
                      <View key={i} style={styles.heatmapCell}>
                        <View style={[styles.heatmapBlock, { backgroundColor: bgColor }]}>
                          <Text style={styles.heatmapBlockText}>{h.orders}</Text>
                        </View>
                        <Text style={styles.heatmapTime}>{h.hour?.split(':')[0] || h.label || `${7 + i}`}</Text>
                      </View>
                    );
                  });
                })()}
              </View>
              <View style={styles.heatmapLegend}>
                <View style={[styles.legendDot, { backgroundColor: colors.success + '60' }]} />
                <Text style={styles.legendLabel}>Low</Text>
                <View style={[styles.legendDot, { backgroundColor: colors.info + '80' }]} />
                <Text style={styles.legendLabel}>Medium</Text>
                <View style={[styles.legendDot, { backgroundColor: colors.warning }]} />
                <Text style={styles.legendLabel}>High</Text>
                <View style={[styles.legendDot, { backgroundColor: colors.error }]} />
                <Text style={styles.legendLabel}>Peak</Text>
              </View>
            </GlassCard>

            {/* Day-of-week heatmap */}
            {data?.daily?.sales_data && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={styles.sectionTitle}>📅 Weekly Congestion Pattern</Text>
                <Text style={styles.sectionSubtitle}>Average orders by day of week (last 4 weeks)</Text>
                <View style={styles.weekHeatmapRow}>
                  {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, di) => {
                    const dayData = (data.daily.sales_data || []).filter((d: any) => {
                                      const dow = new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' });
                                      return dow === day;
                                    });
                    const avgOrders = dayData.length > 0
                      ? Math.round(dayData.reduce((s: number, d: any) => s + (d.orders || 0), 0) / dayData.length)
                      : 0;
                    const maxDaily = Math.max(
                      ...(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => {
                        const dd = (data.daily.sales_data || []).filter((s: any) => {
                          const dow = new Date(s.date).toLocaleDateString('en-US', { weekday: 'short' });
                          return dow === d;
                        });
                        return dd.length > 0
                          ? Math.round(dd.reduce((s: number, r: any) => s + (r.orders || 0), 0) / dd.length)
                          : 0;
                      })),
                      1
                    );
                    const intensity = avgOrders / maxDaily;
                    const bgColor = intensity > 0.75 ? colors.error
                      : intensity > 0.5 ? colors.warning
                      : intensity > 0.25 ? colors.info + '80'
                      : colors.success + '60';
                    return (
                      <View key={di} style={styles.weekCell}>
                        <View style={[styles.weekBlock, { backgroundColor: bgColor }]}>
                          <Text style={styles.weekBlockText}>{avgOrders}</Text>
                        </View>
                        <Text style={styles.weekDayLabel}>{day}</Text>
                      </View>
                    );
                  })}
                </View>
                <Text style={{ fontSize: 11, color: colors.textMuted, marginTop: 8, textAlign: 'center' }}>
                  🎯 Shows which weekdays are busiest — plan staff accordingly
                </Text>
              </GlassCard>
            )}

            {/* Insights */}
            <AICard
              icon="🔥"
              title="Congestion Insights"
              description={data?.peak?.peak_periods?.length > 0
                ? `Peak congestion detected at ${data.peak.peak_periods.slice(0, 2).map((p: any) => p.label).join(' and ')}. Consider adjusting slot capacities for these windows.`
                : 'Low overall congestion. Your slot capacity is well-balanced.'}
              severity={data?.peak?.peak_periods?.length > 0 ? 'warning' : 'info'}
              confidence={0.85}
            />
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
  tabContent: { paddingHorizontal: spacing.lg, gap: spacing.sm, paddingVertical: 12 },
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
  // Yearly tab styles
  insightsList: { gap: 8 },
  insightRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  insightDot: { fontSize: 16, color: colors.primary },
  insightText: { fontSize: 14, color: colors.textSecondary, flex: 1 },

  // ── Heatmap styles ────────────────────────────────────────────
  heatmapGrid: {
    flexDirection: 'row', flexWrap: 'wrap', gap: 6, justifyContent: 'center',
  },
  heatmapCell: { alignItems: 'center', width: '12%', marginBottom: 8 },
  heatmapBlock: {
    width: 36, height: 36, borderRadius: 8,
    justifyContent: 'center', alignItems: 'center',
  },
  heatmapBlockText: { fontSize: 12, fontWeight: '700', color: colors.textInverse },
  heatmapTime: { fontSize: 9, color: colors.textMuted, marginTop: 2 },
  heatmapLegend: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, marginTop: spacing.md,
  },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendLabel: { fontSize: 11, color: colors.textMuted },
  weekHeatmapRow: {
    flexDirection: 'row', justifyContent: 'space-around', gap: 4,
  },
  weekCell: { alignItems: 'center', flex: 1 },
  weekBlock: {
    width: 40, height: 40, borderRadius: 10,
    justifyContent: 'center', alignItems: 'center',
  },
  weekBlockText: { fontSize: 13, fontWeight: '700', color: colors.textInverse },
  weekDayLabel: { fontSize: 9, color: colors.textMuted, marginTop: 4 },
});
