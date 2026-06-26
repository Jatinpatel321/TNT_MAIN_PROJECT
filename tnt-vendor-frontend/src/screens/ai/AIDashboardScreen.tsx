import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { aiApi } from '../../services/aiApi';

type TabType = 'forecast' | 'items' | 'peak' | 'insights' | 'recommendations';

export default function AIDashboardScreen({ navigation }: any) {
  const [activeTab, setActiveTab] = useState<TabType>('forecast');
  const [dailyForecast, setDailyForecast] = useState<any>(null);
  const [weeklyForecast, setWeeklyForecast] = useState<any>(null);
  const [popularItems, setPopularItems] = useState<any>(null);
  const [peakTimes, setPeakTimes] = useState<any>(null);
  const [wasteInsights, setWasteInsights] = useState<any>(null);
  const [inventorySuggestions, setInventorySuggestions] = useState<any>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    try {
      const [
        dailyRes,
        weeklyRes,
        popularRes,
        peakRes,
        wasteRes,
        inventoryRes,
        recRes,
      ] = await Promise.all([
        aiApi.getDailyForecast(),
        aiApi.getWeeklyForecast(),
        aiApi.getPopularItems(),
        aiApi.getPeakTimes(),
        aiApi.getWasteInsights(),
        aiApi.getInventorySuggestions(),
        aiApi.getRecommendations(),
      ]);
      setDailyForecast(dailyRes.data);
      setWeeklyForecast(weeklyRes.data);
      setPopularItems(popularRes.data);
      setPeakTimes(peakRes.data);
      setWasteInsights(wasteRes.data);
      setInventorySuggestions(inventoryRes.data);
      setRecommendations(recRes.data);
    } catch (error) {
      console.error('Failed to load AI data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#EF4444';
      case 'medium': return '#F59E0B';
      case 'low': return '#10B981';
      default: return '#6B7280';
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'increase_capacity': return '📈';
      case 'reduce_capacity': return '📉';
      case 'add_staff': return '👥';
      case 'prepare_extra_stock': return '📦';
      default: return '💡';
    }
  };

  const renderForecastTab = () => (
    <ScrollView style={styles.tabContent}>
      {/* Daily Forecast */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📊 Daily Orders Forecast</Text>
        <Text style={styles.cardSubtitle}>Next 7 days</Text>
        <View style={styles.forecastGrid}>
          {dailyForecast?.forecast?.map((day: any, index: number) => (
            <View key={index} style={[styles.forecastBar, { flexDirection: 'row', alignItems: 'center', marginBottom: 8 }]}>
              <Text style={styles.forecastDay}>{day.day_name?.slice(0, 3)}</Text>
              <View style={[styles.bar, { width: `${Math.min(100, day.predicted_orders * 5)}%`, backgroundColor: day.predicted_orders > 20 ? '#10B981' : '#3B82F6' }]}>
                <Text style={styles.barText}>{day.predicted_orders}</Text>
              </View>
            </View>
          ))}
        </View>
        <View style={styles.forecastSummary}>
          <Text style={styles.summaryText}>Daily Avg: {dailyForecast?.daily_average}</Text>
          <Text style={styles.summaryText}>Total: {dailyForecast?.total_predicted}</Text>
          <Text style={[styles.summaryText, { color: '#10B981', fontWeight: '600' }]}>
            {dailyForecast?.recommendation}
          </Text>
        </View>
      </View>

      {/* Weekly Forecast */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📈 Weekly Forecast</Text>
        <Text style={styles.cardSubtitle}>Next 4 weeks</Text>
        {weeklyForecast?.forecast?.map((week: any, index: number) => (
          <View key={index} style={styles.weekRow}>
            <Text style={styles.weekLabel}>Week {index + 1}</Text>
            <Text style={styles.weekValue}>{week.predicted_orders} orders</Text>
            <Text style={[styles.weekTrend, { color: week.trend === 'up' ? '#10B981' : week.trend === 'down' ? '#EF4444' : '#6B7280' }]}>
              {week.trend === 'up' ? '↑' : week.trend === 'down' ? '↓' : '→'} {week.trend}
            </Text>
          </View>
        ))}
        <View style={styles.forecastSummary}>
          <Text style={styles.summaryText}>Trend: {weeklyForecast?.trend_direction === 'up' ? '📈 Growing' : weeklyForecast?.trend_direction === 'down' ? '📉 Declining' : '➡️ Stable'}</Text>
        </View>
      </View>
    </ScrollView>
  );

  const renderItemsTab = () => (
    <ScrollView style={styles.tabContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🔥 Popular Items</Text>
        <Text style={styles.cardSubtitle}>Top selling items (last 30 days)</Text>
        {popularItems?.popular_items?.map((item: any, index: number) => (
          <View key={index} style={styles.itemRow}>
            <View style={styles.rankBadge}>
              <Text style={styles.rankText}>#{index + 1}</Text>
            </View>
            <View style={styles.itemInfo}>
              <Text style={styles.itemName}>{item.name}</Text>
              <Text style={styles.itemPrice}>₹{item.price}</Text>
            </View>
            <View style={styles.itemStats}>
              <Text style={styles.itemCount}>{item.order_count}x</Text>
              <Text style={[styles.itemTrend, { color: item.trend === 'up' ? '#10B981' : item.trend === 'down' ? '#EF4444' : '#6B7280' }]}>
                {item.trend === 'up' ? '↑' : item.trend === 'down' ? '↓' : '→'} {item.popularity_percentage}%
              </Text>
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  );

  const renderPeakTab = () => (
    <ScrollView style={styles.tabContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>⏰ Peak Time Analysis</Text>
        <Text style={styles.cardSubtitle}>Hourly order distribution</Text>
        {peakTimes?.peak_hours?.map((peak: any, index: number) => (
          <View key={index} style={[styles.forecastBar, { flexDirection: 'row', alignItems: 'center', marginBottom: 8 }]}>
            <Text style={styles.forecastDay}>{peak.hour}:00</Text>
            <View style={[styles.bar, { width: `${Math.min(100, peak.percentage * 3)}%`, backgroundColor: peak.is_peak ? '#F59E0B' : '#93C5FD' }]}>
              <Text style={styles.barText}>{peak.percentage}%</Text>
            </View>
          </View>
        ))}
      </View>

      {peakTimes?.peak_periods && peakTimes.peak_periods.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>🔴 Peak Periods</Text>
          {peakTimes.peak_periods.map((period: any, index: number) => (
            <View key={index} style={styles.peakPeriod}>
              <Text style={styles.peakLabel}>{period.label}</Text>
              <Text style={styles.peakIntensity}>Intensity: {period.intensity}%</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );

  const renderInsightsTab = () => (
    <ScrollView style={styles.tabContent}>
      {/* Waste Insights */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>♻️ Waste Reduction Insights</Text>
        <View style={styles.wasteMetric}>
          <Text style={styles.wasteLabel}>Cancellation Rate</Text>
          <Text style={[styles.wasteValue, { color: (wasteInsights?.cancellation_rate || 0) > 10 ? '#EF4444' : '#10B981' }]}>
            {wasteInsights?.cancellation_rate}%
          </Text>
        </View>
        {wasteInsights?.insights?.map((insight: string, index: number) => (
          <View key={index} style={styles.insightRow}>
            <Text style={styles.bullet}>•</Text>
            <Text style={styles.insightText}>{insight}</Text>
          </View>
        ))}
      </View>

      {/* Inventory Suggestions */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📦 Inventory Suggestions</Text>
        <Text style={styles.cardSubtitle}>{inventorySuggestions?.summary}</Text>
        {inventorySuggestions?.suggestions?.slice(0, 8)?.map((suggestion: any, index: number) => (
          <View key={index} style={styles.suggestionRow}>
            <Text style={[
              styles.suggestionAction,
              { color: suggestion.suggested_action === 'increase_stock' ? '#10B981' : suggestion.suggested_action === 'reduce_stock' ? '#EF4444' : '#F59E0B' }
            ]}>
              {suggestion.suggested_action === 'increase_stock' ? '📈' : suggestion.suggested_action === 'reduce_stock' ? '📉' : '➡️'}
            </Text>
            <View style={styles.suggestionInfo}>
              <Text style={styles.suggestionName}>{suggestion.name}</Text>
              <Text style={styles.suggestionReason}>{suggestion.reason}</Text>
            </View>
            <Text style={styles.suggestionDemand}>{suggestion.demand_percentage}%</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );

  const renderRecommendationsTab = () => (
    <ScrollView style={styles.tabContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🎯 AI Recommendations</Text>
        {recommendations?.length > 0 ? recommendations.map((rec: any, index: number) => (
          <View key={index} style={[styles.recommendationCard, { borderLeftColor: getPriorityColor(rec.priority) }]}>
            <View style={styles.recHeader}>
              <Text style={styles.recIcon}>{getActionIcon(rec.action)}</Text>
              <View style={styles.recInfo}>
                <Text style={styles.recAction}>{rec.action.replace(/_/g, ' ').toUpperCase()}</Text>
                <Text style={styles.recMessage}>{rec.message}</Text>
              </View>
              <View style={[styles.priorityBadge, { backgroundColor: getPriorityColor(rec.priority) }]}>
                <Text style={styles.priorityText}>{rec.priority}</Text>
              </View>
            </View>
          </View>
        )) : (
          <Text style={styles.emptyText}>No recommendations yet. Data is being analyzed.</Text>
        )}
      </View>
    </ScrollView>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading AI insights...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>AI Dashboard</Text>
        <Text style={styles.headerSubtitle}>Intelligent insights for {user?.vendor_name}</Text>
      </View>

      {/* Tab Selector */}
      <View style={styles.tabContainer}>
        <TouchableOpacity style={[styles.tab, activeTab === 'forecast' && styles.activeTab]} onPress={() => setActiveTab('forecast')}>
          <Text style={[styles.tabText, activeTab === 'forecast' && styles.activeTabText]}>📊 Forecast</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'items' && styles.activeTab]} onPress={() => setActiveTab('items')}>
          <Text style={[styles.tabText, activeTab === 'items' && styles.activeTabText]}>🔥 Items</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'peak' && styles.activeTab]} onPress={() => setActiveTab('peak')}>
          <Text style={[styles.tabText, activeTab === 'peak' && styles.activeTabText]}>⏰ Peak</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'insights' && styles.activeTab]} onPress={() => setActiveTab('insights')}>
          <Text style={[styles.tabText, activeTab === 'insights' && styles.activeTabText]}>💡 Insights</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'recommendations' && styles.activeTab]} onPress={() => setActiveTab('recommendations')}>
          <Text style={[styles.tabText, activeTab === 'recommendations' && styles.activeTabText]}>🎯 Recs</Text>
        </TouchableOpacity>
      </View>

      {/* Tab Content */}
      {activeTab === 'forecast' && renderForecastTab()}
      {activeTab === 'items' && renderItemsTab()}
      {activeTab === 'peak' && renderPeakTab()}
      {activeTab === 'insights' && renderInsightsTab()}
      {activeTab === 'recommendations' && renderRecommendationsTab()}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 16,
    color: '#6B7280',
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#10B981',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: 4,
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 4,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#F3F5F9',
    alignItems: 'center',
  },
  activeTab: {
    backgroundColor: '#10B981',
  },
  tabText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#6B7280',
  },
  activeTabText: {
    color: 'white',
  },
  tabContent: {
    padding: 16,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 4,
  },
  cardSubtitle: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 12,
  },
  forecastGrid: {
    marginBottom: 12,
  },
  forecastBar: {
    marginBottom: 8,
  },
  forecastDay: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
    width: 35,
  },
  bar: {
    height: 24,
    borderRadius: 6,
    justifyContent: 'center',
    paddingHorizontal: 8,
    minWidth: 30,
  },
  barText: {
    color: 'white',
    fontSize: 11,
    fontWeight: '600',
  },
  forecastSummary: {
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    paddingTop: 12,
    gap: 4,
  },
  summaryText: {
    fontSize: 14,
    color: '#6B7280',
  },
  weekRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  weekLabel: {
    fontSize: 14,
    color: '#374151',
    fontWeight: '500',
  },
  weekValue: {
    fontSize: 14,
    color: '#111827',
    fontWeight: '600',
  },
  weekTrend: {
    fontSize: 12,
    fontWeight: '600',
  },
  itemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  rankBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#FEF3C7',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  rankText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#D97706',
  },
  itemInfo: {
    flex: 1,
  },
  itemName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
  },
  itemPrice: {
    fontSize: 12,
    color: '#6B7280',
  },
  itemStats: {
    alignItems: 'flex-end',
  },
  itemCount: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#10B981',
  },
  itemTrend: {
    fontSize: 11,
    fontWeight: '600',
  },
  peakPeriod: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  peakLabel: {
    fontSize: 14,
    color: '#374151',
    fontWeight: '500',
  },
  peakIntensity: {
    fontSize: 14,
    color: '#F59E0B',
    fontWeight: '600',
  },
  wasteMetric: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
    marginBottom: 8,
  },
  wasteLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
  },
  wasteValue: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  insightRow: {
    flexDirection: 'row',
    paddingVertical: 4,
  },
  bullet: {
    fontSize: 14,
    color: '#10B981',
    marginRight: 8,
  },
  insightText: {
    fontSize: 14,
    color: '#6B7280',
    flex: 1,
  },
  suggestionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  suggestionAction: {
    fontSize: 18,
    marginRight: 12,
  },
  suggestionInfo: {
    flex: 1,
  },
  suggestionName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
  },
  suggestionReason: {
    fontSize: 12,
    color: '#6B7280',
  },
  suggestionDemand: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#10B981',
  },
  recommendationCard: {
    borderLeftWidth: 4,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    backgroundColor: '#F9FAFB',
  },
  recHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  recIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  recInfo: {
    flex: 1,
  },
  recAction: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#374151',
    letterSpacing: 0.5,
  },
  recMessage: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 2,
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  priorityText: {
    color: 'white',
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  emptyText: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
    paddingVertical: 20,
  },
});