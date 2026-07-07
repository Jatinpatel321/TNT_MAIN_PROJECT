// ─── Premium Smart Demand Dashboard ─────────────────────────────
// AI-powered demand, stock & rush prediction with premium design

import React, {useCallback, useEffect, useRef, useState} from 'react';
import {
  ActivityIndicator,
  Animated,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import {vendorApi, type DemandDashboard} from '../../services/vendorApi';
import {colors, spacing} from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatCard from '../../design-system/components/StatCard';
import StatusPill from '../../design-system/components/StatusPill';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';

type Section = 'demand' | 'stock' | 'rush';

export default function SmartDemandDashboard() {
  const [data, setData] = useState<DemandDashboard | null>(null);
  const [activeSection, setActiveSection] = useState<Section>('demand');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {toValue: 1, duration: 400, useNativeDriver: true}).start();
    loadDashboard();
  }, []);

  const loadDashboard = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      setError(null);
      const response = await vendorApi.getDemandDashboard();
      setData(response.data);
    } catch (err: any) {
      setError(err?.message || 'Unable to load demand dashboard');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const onRefresh = () => { setRefreshing(true); loadDashboard(true); };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading smart demand data...</Text>
      </View>
    );
  }

  const overview = data?.demand_overview;
  const stock = data?.stock_prediction;
  const rush = data?.rush_prediction;

  return (
    <ScrollView
      style={styles.container}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Smart Demand</Text>
        <Text style={styles.headerSubtitle}>AI-powered demand, stock & rush forecasts</Text>
      </View>

      {error && (
        <GlassCard padding={14} borderRadius={16} style={{marginHorizontal: spacing.lg, marginTop: spacing.md, backgroundColor: colors.errorPale}}>
          <Text style={{color: colors.error, fontSize: 14}}>{error}</Text>
          <TouchableOpacity onPress={() => loadDashboard()}><Text style={{color: colors.error, fontWeight: '700', marginTop: 8}}>Retry</Text></TouchableOpacity>
        </GlassCard>
      )}

      <Animated.View style={{opacity: fadeAnim}}>
        {/* Segmented Control */}
        <View style={styles.segmentedWrap}>
          {(['demand', 'stock', 'rush'] as Section[]).map(s => (
            <TouchableOpacity key={s} style={[styles.segment, activeSection === s && styles.segmentActive]} onPress={() => setActiveSection(s)}>
              <Text style={[styles.segmentText, activeSection === s && styles.segmentTextActive]}>{s.toUpperCase()}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Demand Section */}
        {activeSection === 'demand' && (
          <View style={styles.sectionPad}>
            <GlassCard padding={16} borderRadius={18}>
              <Text style={styles.cardTitle}>Demand Forecast</Text>
              <View style={styles.metricGrid}>
                <StatCard value={overview?.orders_today ?? 0} label="Orders Today" icon="📦" color={colors.primary} size="sm" style={{flex: 1}} />
                <StatCard value={overview?.predicted_today ?? 0} label="Predicted" icon="🔮" color={colors.secondary} size="sm" style={{flex: 1}} />
                <StatCard value={overview?.predicted_remaining ?? 0} label="Remaining" icon="⏳" color={colors.warning} size="sm" style={{flex: 1}} />
                <StatCard value={overview?.tomorrow_prediction ?? 0} label="Tomorrow" icon="📅" color={colors.info} size="sm" style={{flex: 1}} />
              </View>
              {overview && (
                <View style={styles.insightList}>
                  <InsightRow label="Weekly trend" value={`${overview.weekly_trend || 'stable'} (${overview.weekly_change_pct ?? 0}%)`} />
                  <InsightRow label="Vs yesterday" value={`${overview.vs_yesterday_pct ?? 0}%`} />
                  <InsightRow label="Daily avg" value={`${overview.daily_average ?? 0} orders`} />
                </View>
              )}
            </GlassCard>

            {data && data.recommendations && data.recommendations.length > 0 && (
              <GlassCard padding={16} borderRadius={18} style={{marginTop: spacing.sm}}>
                <Text style={styles.cardTitle}>AI Recommendations</Text>
                {data.recommendations.slice(0, 5).map((rec: any, i: number) => (
                  <View key={i} style={styles.recRow}>
                    <Text style={styles.recBullet}>•</Text>
                    <Text style={styles.recText}>{rec.message}</Text>
                  </View>
                ))}
              </GlassCard>
            )}
          </View>
        )}

        {/* Stock Section */}
        {activeSection === 'stock' && (
          <View style={styles.sectionPad}>
            <GlassCard padding={16} borderRadius={18}>
              <Text style={styles.cardTitle}>Stock Prediction</Text>
              <View style={styles.metricGrid}>
                <StatCard value={stock?.summary?.total_items ?? 0} label="Total Items" icon="📦" color={colors.primary} size="sm" style={{flex: 1}} />
                <StatCard value={stock?.summary?.critical ?? 0} label="Critical" icon="🔴" color={colors.error} size="sm" style={{flex: 1}} />
                <StatCard value={stock?.summary?.low ?? 0} label="Low" icon="🟡" color={colors.warning} size="sm" style={{flex: 1}} />
                <StatCard value={stock?.summary?.ok ?? 0} label="OK" icon="🟢" color={colors.success} size="sm" style={{flex: 1}} />
              </View>
            </GlassCard>
            {(stock?.items ?? []).slice(0, 10).map((item: any) => {
              const urgencyColor = item.urgency === 'critical' ? colors.error : item.urgency === 'low' ? colors.warning : colors.success;
              return (
                <GlassCard key={item.item_id} padding={14} borderRadius={16} style={{marginTop: spacing.sm}}>
                  <View style={styles.stockRow}>
                    <View style={{flex: 1}}>
                      <Text style={styles.stockName}>{item.name}</Text>
                      <Text style={styles.stockMeta}>Stock {item.current_stock} / demand {item.daily_demand_rate}/day</Text>
                    </View>
                    <StatusPill label={item.urgency} variant={item.urgency === 'critical' ? 'error' : item.urgency === 'low' ? 'warning' : 'success'} size="sm" />
                  </View>
                </GlassCard>
              );
            })}
          </View>
        )}

        {/* Rush Section */}
        {activeSection === 'rush' && (
          <View style={styles.sectionPad}>
            <GlassCard padding={16} borderRadius={18}>
              <Text style={styles.cardTitle}>Rush Prediction</Text>
              <View style={styles.metricGrid}>
                <StatCard value={rush?.rush_hours_count ?? 0} label="Rush Hours" icon="⚡" color={colors.warning} size="sm" style={{flex: 1}} />
                <StatCard value={rush?.next_rush_hour ?? 0} label="Next Rush Hour" icon="⏰" color={colors.info} size="sm" style={{flex: 1}} />
                <StatCard value={rush?.busiest_hour ?? 0} label="Busiest Hour" icon="🏆" color={colors.error} size="sm" style={{flex: 1}} />
              </View>
              {rush?.staff_recommendation && (
                <View style={styles.insightBox}>
                  <Text style={styles.insightIcon}>💡</Text>
                  <Text style={styles.insightBoxText}>{rush.staff_recommendation}</Text>
                </View>
              )}
            </GlassCard>

            {(rush?.predictions ?? []).map((hour: any) => {
              const isRush = hour.is_rush;
              return (
                <GlassCard key={hour.hour} padding={12} borderRadius={14} style={{marginTop: 6}}>
                  <View style={styles.rushRow}>
                    <Text style={styles.rushLabel}>{hour.label}</Text>
                    <View style={styles.rushBarTrack}>
                      <View style={[styles.rushBar, {width: `${Math.min(100, hour.percentage)}%`, backgroundColor: isRush ? colors.warning : colors.success}]} />
                    </View>
                    <Text style={styles.rushCount}>{hour.predicted_orders}</Text>
                  </View>
                </GlassCard>
              );
            })}
            <View style={{height: spacing.huge}} />
          </View>
        )}
      </Animated.View>
    </ScrollView>
  );
}

function InsightRow({label, value}: {label: string; value: string}) {
  return (
    <View style={insightStyles.row}>
      <Text style={insightStyles.label}>{label}</Text>
      <Text style={insightStyles.value}>{value}</Text>
    </View>
  );
}
const insightStyles = StyleSheet.create({
  row: {flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderTopWidth: 1, borderTopColor: colors.borderLight},
  label: {fontSize: 13, color: colors.textMuted},
  value: {fontSize: 14, fontWeight: '600', color: colors.textPrimary},
});

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.bg},
  centered: {flex: 1, justifyContent: 'center', alignItems: 'center'},
  loadingText: {marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600'},
  header: {
    backgroundColor: colors.primary, paddingTop: spacing.huge + 20, paddingBottom: spacing.xxl, paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28, borderBottomRightRadius: 28, overflow: 'hidden',
  },
  headerDeco1: {position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)'},
  headerDeco2: {position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)'},
  headerTitle: {fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3},
  headerSubtitle: {fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500'},
  segmentedWrap: {flexDirection: 'row', gap: 8, paddingHorizontal: spacing.lg, marginTop: spacing.md, marginBottom: spacing.sm},
  segment: {flex: 1, alignItems: 'center', borderWidth: 1.5, borderColor: colors.border, borderRadius: 12, paddingVertical: 10, backgroundColor: colors.bgCard},
  segmentActive: {backgroundColor: colors.textPrimary, borderColor: colors.textPrimary},
  segmentText: {fontSize: 12, fontWeight: '700', color: colors.textMuted},
  segmentTextActive: {color: colors.textInverse},
  sectionPad: {paddingHorizontal: spacing.lg},
  cardTitle: {fontSize: 17, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.sm},
  metricGrid: {flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginBottom: spacing.sm},
  insightList: {marginTop: spacing.xs},
  insightBox: {flexDirection: 'row', backgroundColor: colors.infoPale, borderRadius: 12, padding: 12, gap: 8, marginTop: spacing.sm},
  insightIcon: {fontSize: 16},
  insightBoxText: {flex: 1, fontSize: 13, color: colors.info, lineHeight: 18},
  recRow: {flexDirection: 'row', marginBottom: 6, gap: 6},
  recBullet: {color: colors.primary, fontSize: 14, fontWeight: '700'},
  recText: {flex: 1, fontSize: 13, color: colors.textSecondary, lineHeight: 18},
  stockRow: {flexDirection: 'row', alignItems: 'center', gap: 12},
  stockName: {fontSize: 15, fontWeight: '600', color: colors.textPrimary},
  stockMeta: {fontSize: 12, color: colors.textMuted, marginTop: 2},
  rushRow: {flexDirection: 'row', alignItems: 'center', gap: 8},
  rushLabel: {width: 80, fontSize: 12, color: colors.textSecondary},
  rushBarTrack: {flex: 1, height: 10, borderRadius: 999, backgroundColor: colors.bgSecondary, overflow: 'hidden'},
  rushBar: {height: 10, borderRadius: 999},
  rushCount: {width: 28, textAlign: 'right', fontSize: 12, fontWeight: '700', color: colors.textPrimary},
});
