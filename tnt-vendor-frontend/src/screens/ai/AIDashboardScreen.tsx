// ─── AI Dashboard ─────────────────────────────────────────────────
// Premium AI-powered insights with forecasts, recommendations, and analytics

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
import { aiApi } from '../../services/aiApi';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatCard from '../../design-system/components/StatCard';
import ForecastCard from '../../design-system/components/ForecastCard';
import AICard from '../../design-system/components/AICard';
import Badge from '../../design-system/components/Badge';

type TabType = 'forecast' | 'items' | 'peak' | 'insights' | 'recommendations';

export default function AIDashboardScreen({ navigation }: any) {
  const [activeTab, setActiveTab] = useState<TabType>('forecast');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<any>(null);
  const { user } = useAuth();

  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    loadData();
  }, []);

  const loadData = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      const [dailyRes, itemsRes, peakRes, wasteRes, inventoryRes, recRes] = await Promise.all([
        aiApi.getDailyForecast(),
        aiApi.getPopularItems(),
        aiApi.getPeakTimes(),
        aiApi.getWasteInsights(),
        aiApi.getInventorySuggestions(),
        aiApi.getRecommendations(),
      ]);
      setData({
        forecast: dailyRes.data,
        items: itemsRes.data,
        peak: peakRes.data,
        waste: wasteRes.data,
        inventory: inventoryRes.data,
        recommendations: recRes.data,
      });
    } catch (err) {
      console.error('AI data load error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'forecast', label: 'Forecast', icon: '📊' },
    { key: 'items', label: 'Items', icon: '🔥' },
    { key: 'peak', label: 'Peak', icon: '⏰' },
    { key: 'insights', label: 'Insights', icon: '💡' },
    { key: 'recommendations', label: 'Recs', icon: '🎯' },
  ];

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading AI insights...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>AI Insights</Text>
        <Text style={styles.headerSubtitle}>Intelligent predictions for {user?.vendor_name}</Text>
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
        style={styles.tabContentScroll}
      >
        {/* Forecast Tab */}
        {activeTab === 'forecast' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <ForecastCard
              title="Daily Orders Forecast"
              icon="📊"
              color={colors.primary}
              data={(data?.forecast?.forecast || []).slice(0, 5).map((d: any) => ({
                label: d.day_name?.slice(0, 3) || 'Day',
                value: d.predicted_orders,
                unit: 'orders',
              }))}
              style={{ marginBottom: spacing.md }}
            />
            <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
              <Text style={styles.sectionTitle}>📈 Forecast Summary</Text>
              {data?.forecast?.forecast?.map((day: any, i: number) => (
                <View key={i} style={styles.forecastRow}>
                  <Text style={styles.dayLabel}>{day.day_name?.slice(0, 3)}</Text>
                  <View style={styles.forecastBarTrack}>
                    <View style={[styles.forecastBar, { width: `${Math.min(100, (day.predicted_orders / (data.forecast.daily_average || 20)) * 50)}%` }]} />
                  </View>
                  <Text style={styles.forecastValue}>{day.predicted_orders}</Text>
                </View>
              ))}
              <View style={styles.forecastSummary}>
                <Text style={styles.summaryText}>Daily Avg: {data?.forecast?.daily_average || '—'}</Text>
                <Text style={styles.summaryText}>Total: {data?.forecast?.total_predicted || '—'}</Text>
              </View>
            </GlassCard>
          </Animated.View>
        )}

        {/* Items Tab */}
        {activeTab === 'items' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
              <Text style={styles.sectionTitle}>🔥 Popular Items</Text>
              <Text style={styles.sectionSubtitle}>Top selling items this period</Text>
              {(data?.items?.popular_items || []).map((item: any, i: number) => (
                <View key={i} style={styles.itemRow}>
                  <View style={styles.rankBadge}>
                    <Text style={styles.rankText}>#{i + 1}</Text>
                  </View>
                  <View style={styles.itemInfo}>
                    <Text style={styles.itemName}>{item.name}</Text>
                    <Text style={styles.itemMeta}>₹{item.price} · {item.order_count} orders</Text>
                  </View>
                  <Badge
                    label={item.trend === 'up' ? '↑ Growing' : item.trend === 'down' ? '↓ Declining' : '→ Stable'}
                    variant={item.trend === 'up' ? 'success' : item.trend === 'down' ? 'error' : 'neutral'}
                    size="sm"
                  />
                </View>
              ))}
            </GlassCard>
          </Animated.View>
        )}

        {/* Peak Tab */}
        {activeTab === 'peak' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <ForecastCard
              title="Peak Time Analysis"
              icon="⏰"
              color={colors.warning}
              data={(data?.peak?.peak_hours || []).slice(0, 8).map((p: any) => ({
                label: `${p.hour}:00`,
                value: p.percentage,
                unit: '%',
              }))}
              style={{ marginBottom: spacing.md }}
            />
            {(data?.peak?.peak_periods || []).length > 0 && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={styles.sectionTitle}>🔴 Peak Periods</Text>
                {data.peak.peak_periods.map((period: any, i: number) => (
                  <View key={i} style={styles.peakPeriodRow}>
                    <Text style={styles.peakLabel}>{period.label}</Text>
                    <Badge label={`${period.intensity}% intensity`} variant="warning" size="sm" />
                  </View>
                ))}
              </GlassCard>
            )}
          </Animated.View>
        )}

        {/* Insights Tab */}
        {activeTab === 'insights' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <AICard
              icon="♻️"
              title="Waste Reduction"
              description={`Cancellation rate: ${data?.waste?.cancellation_rate || 0}%. ${(data?.waste?.insights || ['No insights available'])[0]}`}
              severity={((data?.waste?.cancellation_rate || 0) > 10) ? 'warning' : 'success'}
              confidence={0.85}
            />
            <View style={{ height: spacing.sm }} />
            <AICard
              icon="📦"
              title="Inventory Intelligence"
              description={data?.inventory?.summary || 'Predictions based on historical ordering patterns.'}
              severity="info"
              action={{ label: 'View Inventory', onPress: () => navigation.navigate('InventoryPlanning') }}
              confidence={0.82}
            />
            {(data?.inventory?.suggestions || []).length > 0 && (
              <View style={{ marginTop: spacing.md }}>
                <Text style={styles.sectionTitle}>📦 Stock Suggestions</Text>
                {data.inventory.suggestions.slice(0, 5).map((s: any, i: number) => (
                  <GlassCard key={i} padding={12} borderRadius={14} style={{ marginBottom: 6 }}>
                    <View style={styles.suggestionRow}>
                      <Text style={styles.suggestionIcon}>
                        {s.suggested_action === 'increase_stock' ? '📈' : s.suggested_action === 'reduce_stock' ? '📉' : '➡️'}
                      </Text>
                      <View style={styles.suggestionInfo}>
                        <Text style={styles.suggestionName}>{s.name}</Text>
                        <Text style={styles.suggestionReason}>{s.reason}</Text>
                      </View>
                      <Badge label={`${s.demand_percentage}%`} variant="primary" size="sm" />
                    </View>
                  </GlassCard>
                ))}
              </View>
            )}
          </Animated.View>
        )}

        {/* Recommendations Tab */}
        {activeTab === 'recommendations' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <Text style={styles.sectionTitle}>🎯 AI Recommendations</Text>
            {(data?.recommendations || []).length > 0 ? (
              data.recommendations.map((rec: any, i: number) => (
                <AICard
                  key={i}
                  icon={rec.action === 'increase_capacity' ? '📈' : rec.action === 'add_staff' ? '👥' : rec.action === 'prepare_extra_stock' ? '📦' : '💡'}
                  title={rec.action?.replace(/_/g, ' ').toUpperCase()}
                  description={rec.message}
                  severity={rec.priority === 'high' ? 'warning' : rec.priority === 'medium' ? 'info' : 'success'}
                  confidence={0.9}
                  style={{ marginBottom: spacing.sm }}
                />
              ))
            ) : (
              <GlassCard padding={24} borderRadius={20}>
                <Text style={styles.emptyText}>No recommendations yet. Data is being analyzed.</Text>
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
  tabContentScroll: { paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  tab: {
    flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10,
    borderRadius: 14, backgroundColor: colors.bgCard, marginRight: 8, gap: 6,
    borderWidth: 1.5, borderColor: colors.border, ...shadows.sm,
  },
  tabActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  tabIcon: { fontSize: 14 },
  tabText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary },
  tabTextActive: { color: colors.textInverse },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: 12 },
  sectionSubtitle: { fontSize: 12, color: colors.textMuted, marginBottom: spacing.md },
  forecastRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 8 },
  dayLabel: { fontSize: 13, fontWeight: '600', color: colors.textSecondary, width: 35 },
  forecastBarTrack: { flex: 1, height: 22, backgroundColor: colors.bgTertiary, borderRadius: 6, overflow: 'hidden' },
  forecastBar: { height: '100%', backgroundColor: colors.primary, borderRadius: 6, minWidth: 30 },
  forecastValue: { fontSize: 14, fontWeight: '700', color: colors.textPrimary, width: 40, textAlign: 'right' },
  forecastSummary: { borderTopWidth: 1, borderTopColor: colors.borderLight, paddingTop: 12, gap: 4 },
  summaryText: { fontSize: 13, color: colors.textSecondary },
  itemRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.borderLight },
  rankBadge: { width: 28, height: 28, borderRadius: 14, backgroundColor: colors.warningPale, justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  rankText: { fontSize: 12, fontWeight: '700', color: colors.warningDark },
  itemInfo: { flex: 1 },
  itemName: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  itemMeta: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  peakPeriodRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.borderLight },
  peakLabel: { fontSize: 14, fontWeight: '500', color: colors.textPrimary },
  suggestionRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  suggestionIcon: { fontSize: 18 },
  suggestionInfo: { flex: 1 },
  suggestionName: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  suggestionReason: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  emptyText: { fontSize: 14, color: colors.textMuted, textAlign: 'center' },
});
