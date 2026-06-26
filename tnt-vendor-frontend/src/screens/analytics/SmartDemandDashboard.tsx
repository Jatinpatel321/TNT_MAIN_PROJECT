import React, {useCallback, useEffect, useState} from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import {vendorApi, type DemandDashboard} from '../../services/vendorApi';

type Section = 'demand' | 'stock' | 'rush';

export default function SmartDemandDashboard() {
  const [data, setData] = useState<DemandDashboard | null>(null);
  const [activeSection, setActiveSection] = useState<Section>('demand');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const onRefresh = () => {
    setRefreshing(true);
    loadDashboard(true);
  };

  const overview = data?.demand_overview;
  const stock = data?.stock_prediction;
  const rush = data?.rush_prediction;

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#10B981" />
        <Text style={styles.loadingText}>Loading smart demand data...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
      <View style={styles.header}>
        <Text style={styles.title}>Smart Demand</Text>
        <Text style={styles.subtitle}>Forecast demand, stock risk, and rush windows</Text>
      </View>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={() => loadDashboard()}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      <View style={styles.segmentedControl}>
        {(['demand', 'stock', 'rush'] as Section[]).map(section => (
          <TouchableOpacity
            key={section}
            style={[styles.segment, activeSection === section && styles.activeSegment]}
            onPress={() => setActiveSection(section)}>
            <Text style={[styles.segmentText, activeSection === section && styles.activeSegmentText]}>
              {section.toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {activeSection === 'demand' && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Demand Forecast</Text>
          <View style={styles.metricGrid}>
            <Metric label="Orders today" value={overview?.orders_today ?? 0} />
            <Metric label="Predicted today" value={overview?.predicted_today ?? 0} />
            <Metric label="Remaining" value={overview?.predicted_remaining ?? 0} />
            <Metric label="Tomorrow" value={overview?.tomorrow_prediction ?? 0} />
          </View>
          <Text style={styles.insightText}>Weekly trend: {overview?.weekly_trend ?? 'stable'} ({overview?.weekly_change_pct ?? 0}%)</Text>
          <Text style={styles.insightText}>Vs yesterday: {overview?.vs_yesterday_pct ?? 0}%</Text>
          <Text style={styles.insightText}>Daily average: {overview?.daily_average ?? 0} orders</Text>
        </View>
      )}

      {activeSection === 'stock' && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Stock Prediction</Text>
          <View style={styles.metricGrid}>
            <Metric label="Total items" value={stock?.summary?.total_items ?? 0} />
            <Metric label="Critical" value={stock?.summary?.critical ?? 0} tone="danger" />
            <Metric label="Low" value={stock?.summary?.low ?? 0} tone="warning" />
            <Metric label="OK" value={stock?.summary?.ok ?? 0} tone="success" />
          </View>
          {(stock?.items ?? []).slice(0, 10).map((item: any) => (
            <View key={item.item_id} style={styles.listRow}>
              <View style={styles.rowMain}>
                <Text style={styles.rowTitle}>{item.name}</Text>
                <Text style={styles.rowSub}>Stock {item.current_stock} / demand {item.daily_demand_rate}/day</Text>
              </View>
              <View style={[styles.pill, getUrgencyStyle(item.urgency)]}>
                <Text style={styles.pillText}>{item.urgency}</Text>
              </View>
            </View>
          ))}
        </View>
      )}

      {activeSection === 'rush' && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Rush Prediction</Text>
          <View style={styles.metricGrid}>
            <Metric label="Rush hours" value={rush?.rush_hours_count ?? 0} />
            <Metric label="Next rush" value={rush?.next_rush_hour != null ? `${rush.next_rush_hour}:00` : 'None'} />
            <Metric label="Busiest" value={rush?.busiest_hour != null ? `${rush.busiest_hour}:00` : 'N/A'} />
          </View>
          <Text style={styles.insightText}>{rush?.staff_recommendation}</Text>
          {(rush?.predictions ?? []).map((hour: any) => (
            <View key={hour.hour} style={styles.rushRow}>
              <Text style={styles.rushLabel}>{hour.label}</Text>
              <View style={styles.rushBarTrack}>
                <View style={[styles.rushBar, {width: `${Math.min(100, hour.percentage)}%`, backgroundColor: hour.is_rush ? '#F59E0B' : '#10B981'}]} />
              </View>
              <Text style={styles.rushCount}>{hour.predicted_orders}</Text>
            </View>
          ))}
        </View>
      )}

      {(data?.recommendations ?? []).length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Recommendations</Text>
          {data?.recommendations.slice(0, 5).map((rec: any, index: number) => (
            <Text key={index} style={styles.insightText}>{rec.message}</Text>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

function getUrgencyStyle(urgency: string) {
  if (urgency === 'critical') return styles.critical;
  if (urgency === 'low') return styles.low;
  return styles.ok;
}

function Metric({label, value, tone}: {label: string; value: string | number; tone?: 'danger' | 'warning' | 'success'}) {
  return (
    <View style={styles.metricCard}>
      <Text style={[styles.metricValue, tone === 'danger' && styles.dangerText, tone === 'warning' && styles.warningText, tone === 'success' && styles.successText]}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#F9FAFB'},
  centered: {flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12},
  loadingText: {fontSize: 14, color: '#6B7280'},
  header: {backgroundColor: '#10B981', padding: 20, paddingTop: 56},
  title: {fontSize: 24, fontWeight: '700', color: 'white'},
  subtitle: {fontSize: 14, color: 'rgba(255,255,255,0.82)', marginTop: 4},
  errorBox: {margin: 16, padding: 12, borderRadius: 8, backgroundColor: '#FEE2E2'},
  errorText: {fontSize: 14, color: '#991B1B'},
  retryText: {fontSize: 14, fontWeight: '700', color: '#991B1B', marginTop: 8},
  segmentedControl: {flexDirection: 'row', gap: 8, padding: 16},
  segment: {flex: 1, alignItems: 'center', borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 8, paddingVertical: 10, backgroundColor: 'white'},
  activeSegment: {backgroundColor: '#111827', borderColor: '#111827'},
  segmentText: {fontSize: 12, fontWeight: '700', color: '#6B7280'},
  activeSegmentText: {color: 'white'},
  card: {backgroundColor: 'white', margin: 16, marginTop: 0, padding: 16, borderRadius: 8, shadowColor: '#000', shadowOffset: {width: 0, height: 1}, shadowOpacity: 0.08, shadowRadius: 3, elevation: 2},
  cardTitle: {fontSize: 18, fontWeight: '700', color: '#111827', marginBottom: 12},
  metricGrid: {flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 12},
  metricCard: {width: '48%', minHeight: 76, borderRadius: 8, backgroundColor: '#F3F4F6', padding: 12, justifyContent: 'center'},
  metricValue: {fontSize: 22, fontWeight: '800', color: '#111827'},
  metricLabel: {fontSize: 12, color: '#6B7280', marginTop: 4},
  dangerText: {color: '#DC2626'},
  warningText: {color: '#D97706'},
  successText: {color: '#059669'},
  insightText: {fontSize: 14, color: '#374151', lineHeight: 20, marginBottom: 6},
  listRow: {flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderTopWidth: 1, borderTopColor: '#F3F4F6'},
  rowMain: {flex: 1},
  rowTitle: {fontSize: 14, fontWeight: '700', color: '#111827'},
  rowSub: {fontSize: 12, color: '#6B7280', marginTop: 2},
  pill: {borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5},
  critical: {backgroundColor: '#FEE2E2'},
  low: {backgroundColor: '#FEF3C7'},
  ok: {backgroundColor: '#D1FAE5'},
  pillText: {fontSize: 11, fontWeight: '800', color: '#111827', textTransform: 'uppercase'},
  rushRow: {flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10},
  rushLabel: {width: 86, fontSize: 12, color: '#374151'},
  rushBarTrack: {flex: 1, height: 10, borderRadius: 999, backgroundColor: '#E5E7EB', overflow: 'hidden'},
  rushBar: {height: 10, borderRadius: 999},
  rushCount: {width: 28, textAlign: 'right', fontSize: 12, fontWeight: '700', color: '#111827'},
});