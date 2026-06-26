import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { analyticsApi } from '../../services/analyticsApi';

type TabType = 'daily' | 'weekly' | 'monthly' | 'items' | 'peak' | 'waste';

export default function AnalyticsDashboard({ navigation }: any) {
  const [activeTab, setActiveTab] = useState<TabType>('daily');
  const [dailySales, setDailySales] = useState<any>(null);
  const [weeklySales, setWeeklySales] = useState<any>(null);
  const [monthlySales, setMonthlySales] = useState<any>(null);
  const [yearlySales, setYearlySales] = useState<any>(null);
  const [itemAnalysis, setItemAnalysis] = useState<any>(null);
  const [peakHours, setPeakHours] = useState<any>(null);
  const [wasteAnalysis, setWasteAnalysis] = useState<any>(null);
  const [revenueTrends, setRevenueTrends] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    try {
      const [dailyRes, weeklyRes, monthlyRes, yearlyRes, itemsRes, peakRes, wasteRes, revenueRes] =
        await Promise.all([
          analyticsApi.getDailySales(),
          analyticsApi.getWeeklySales(),
          analyticsApi.getMonthlySales(),
          analyticsApi.getYearlySales(),
          analyticsApi.getItemAnalysis(),
          analyticsApi.getPeakHours(),
          analyticsApi.getWasteAnalysis(),
          analyticsApi.getRevenueTrends(),
        ]);
      setDailySales(dailyRes.data);
      setWeeklySales(weeklyRes.data);
      setMonthlySales(monthlyRes.data);
      setYearlySales(yearlyRes.data);
      setItemAnalysis(itemsRes.data);
      setPeakHours(peakRes.data);
      setWasteAnalysis(wasteRes.data);
      setRevenueTrends(revenueRes.data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (reportType: string) => {
    try {
      const res = await analyticsApi.exportCsv(reportType);
      Alert.alert('Export Successful', `${reportType}_report.csv downloaded`);
    } catch (error) {
      Alert.alert('Export Failed', 'Could not export report');
    }
  };

  const renderDailyTab = () => (
    <ScrollView style={styles.tabContent}>
      {/* Summary Cards */}
      <View style={styles.summaryRow}>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>₹{dailySales?.total_revenue || 0}</Text>
          <Text style={styles.summaryLabel}>Total Revenue</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>{dailySales?.total_orders || 0}</Text>
          <Text style={styles.summaryLabel}>Total Orders</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>₹{dailySales?.daily_average_revenue || 0}</Text>
          <Text style={styles.summaryLabel}>Daily Avg</Text>
        </View>
      </View>

      {/* Daily Sales Chart (Bar visualization) */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📊 Daily Sales (Last 30 Days)</Text>
        <View style={styles.chartContainer}>
          {dailySales?.sales_data?.slice(-10).map((day: any, index: number) => (
            <View key={index} style={styles.chartBar}>
              <View style={[styles.bar, { height: Math.max(4, (day.revenue / (dailySales.daily_average_revenue * 2)) * 100), backgroundColor: '#10B981' }]} />
              <Text style={styles.barLabel}>{new Date(day.date).getDate()}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Sales Data Table */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📋 Sales Data</Text>
        {dailySales?.sales_data?.slice(-7).reverse().map((day: any, index: number) => (
          <View key={index} style={styles.dataRow}>
            <Text style={styles.dataDate}>{new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</Text>
            <Text style={styles.dataOrders}>{day.orders} orders</Text>
            <Text style={styles.dataRevenue}>₹{day.revenue}</Text>
          </View>
        ))}
      </View>

      <TouchableOpacity style={styles.exportButton} onPress={() => handleExport('daily')}>
        <Text style={styles.exportButtonText}>📥 Export CSV</Text>
      </TouchableOpacity>
    </ScrollView>
  );

  const renderWeeklyTab = () => (
    <ScrollView style={styles.tabContent}>
      <View style={styles.summaryRow}>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>₹{weeklySales?.total_revenue || 0}</Text>
          <Text style={styles.summaryLabel}>Total Revenue</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>{weeklySales?.total_orders || 0}</Text>
          <Text style={styles.summaryLabel}>Total Orders</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={[styles.summaryValue, { color: (weeklySales?.growth_percentage || 0) >= 0 ? '#10B981' : '#EF4444' }]}>
            {weeklySales?.growth_percentage || 0}%
          </Text>
          <Text style={styles.summaryLabel}>Growth</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>📈 Weekly Sales (Last 12 Weeks)</Text>
        <View style={styles.chartContainer}>
          {weeklySales?.weekly_data?.map((week: any, index: number) => (
            <View key={index} style={styles.chartBar}>
              <View style={[styles.bar, { height: Math.max(4, (week.revenue / (weeklySales.weekly_average_revenue * 2)) * 100), backgroundColor: '#3B82F6' }]} />
              <Text style={styles.barLabel}>W{index + 1}</Text>
            </View>
          ))}
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>📋 Weekly Data</Text>
        {weeklySales?.weekly_data?.map((week: any, index: number) => (
          <View key={index} style={styles.dataRow}>
            <Text style={styles.dataDate}>Week {index + 1}</Text>
            <Text style={styles.dataOrders}>{week.orders} orders</Text>
            <Text style={styles.dataRevenue}>₹{week.revenue}</Text>
          </View>
        ))}
      </View>

      <TouchableOpacity style={styles.exportButton} onPress={() => handleExport('weekly')}>
        <Text style={styles.exportButtonText}>📥 Export CSV</Text>
      </TouchableOpacity>
    </ScrollView>
  );

  const renderMonthlyTab = () => (
    <ScrollView style={styles.tabContent}>
      <View style={styles.summaryRow}>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>₹{monthlySales?.total_revenue || 0}</Text>
          <Text style={styles.summaryLabel}>Total Revenue</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>{monthlySales?.total_orders || 0}</Text>
          <Text style={styles.summaryLabel}>Total Orders</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>₹{monthlySales?.monthly_average_revenue || 0}</Text>
          <Text style={styles.summaryLabel}>Monthly Avg</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>📊 Monthly Sales</Text>
        <View style={styles.chartContainer}>
          {monthlySales?.monthly_data?.map((month: any, index: number) => (
            <View key={index} style={styles.chartBar}>
              <View style={[styles.bar, { height: Math.max(4, (month.revenue / (monthlySales.monthly_average_revenue * 2)) * 100), backgroundColor: '#8B5CF6' }]} />
              <Text style={styles.barLabel}>{month.month.slice(0, 3)}</Text>
            </View>
          ))}
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>📋 Monthly Data</Text>
        {monthlySales?.monthly_data?.map((month: any, index: number) => (
          <View key={index} style={styles.dataRow}>
            <Text style={styles.dataDate}>{month.month}</Text>
            <Text style={styles.dataOrders}>{month.orders} orders</Text>
            <Text style={styles.dataRevenue}>₹{month.revenue}</Text>
          </View>
        ))}
      </View>

      {/* Yearly Summary */}
      {yearlySales?.yearly_data && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>📅 Yearly Summary</Text>
          {yearlySales.yearly_data.map((year: any, index: number) => (
            <View key={index} style={styles.dataRow}>
              <Text style={styles.dataDate}>{year.year}</Text>
              <Text style={styles.dataOrders}>{year.orders} orders</Text>
              <Text style={styles.dataRevenue}>₹{year.revenue}</Text>
            </View>
          ))}
        </View>
      )}

      <TouchableOpacity style={styles.exportButton} onPress={() => handleExport('monthly')}>
        <Text style={styles.exportButtonText}>📥 Export CSV</Text>
      </TouchableOpacity>
    </ScrollView>
  );

  const renderItemsTab = () => (
    <ScrollView style={styles.tabContent}>
      {/* Popular Items */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🔥 Popular Items</Text>
        <Text style={styles.cardSubtitle}>Top selling items by order count</Text>
        {itemAnalysis?.popular_items?.map((item: any, index: number) => (
          <View key={index} style={styles.itemRow}>
            <View style={styles.rankBadge}>
              <Text style={styles.rankText}>#{index + 1}</Text>
            </View>
            <View style={styles.itemInfo}>
              <Text style={styles.itemName}>{item.name}</Text>
              <Text style={styles.itemStats}>{item.order_count} orders · {item.total_quantity} units</Text>
            </View>
            <View style={styles.itemRevenue}>
              <Text style={styles.itemRevenueText}>₹{item.total_revenue}</Text>
              <Text style={styles.itemPercentage}>{item.percentage}%</Text>
            </View>
          </View>
        ))}
      </View>

      {/* Low Selling Items */}
      {itemAnalysis?.low_selling_items?.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>📉 Low Selling Items</Text>
          {itemAnalysis.low_selling_items.map((item: any, index: number) => (
            <View key={index} style={styles.itemRow}>
              <View style={[styles.rankBadge, { backgroundColor: '#FEE2E2' }]}>
                <Text style={[styles.rankText, { color: '#EF4444' }]}>#{index + 1}</Text>
              </View>
              <View style={styles.itemInfo}>
                <Text style={styles.itemName}>{item.name}</Text>
                <Text style={styles.itemStats}>{item.order_count} orders · {item.total_quantity} units</Text>
              </View>
              <View style={styles.itemRevenue}>
                <Text style={styles.itemRevenueText}>₹{item.total_revenue}</Text>
                <Text style={[styles.itemPercentage, { color: '#EF4444' }]}>{item.percentage}%</Text>
              </View>
            </View>
          ))}
        </View>
      )}

      <TouchableOpacity style={styles.exportButton} onPress={() => handleExport('items')}>
        <Text style={styles.exportButtonText}>📥 Export CSV</Text>
      </TouchableOpacity>
    </ScrollView>
  );

  const renderPeakTab = () => (
    <ScrollView style={styles.tabContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>⏰ Peak Hour Analysis</Text>
        <Text style={styles.cardSubtitle}>Order distribution by hour of day</Text>
        <View style={styles.peakChart}>
          {peakHours?.hourly_distribution?.map((hour: any, index: number) => (
            <View key={index} style={styles.peakRow}>
              <Text style={styles.peakHour}>{hour.hour}</Text>
              <View style={[styles.peakBar, { width: `${Math.min(100, (hour.orders / (peakHours.total_orders_analyzed / 24)) * 50)}%`, backgroundColor: hour.is_peak ? '#F59E0B' : '#93C5FD' }]}>
                <Text style={styles.peakBarText}>{hour.orders}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {peakHours?.peak_periods?.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>🔴 Peak Periods</Text>
          {peakHours.peak_periods.map((period: any, index: number) => (
            <View key={index} style={styles.peakPeriodRow}>
              <Text style={styles.peakPeriodLabel}>{period.label}</Text>
              <Text style={styles.peakPeriodOrders}>{period.orders} orders</Text>
            </View>
          ))}
        </View>
      )}

      <TouchableOpacity style={styles.exportButton} onPress={() => handleExport('peak_hours')}>
        <Text style={styles.exportButtonText}>📥 Export CSV</Text>
      </TouchableOpacity>
    </ScrollView>
  );

  const renderWasteTab = () => (
    <ScrollView style={styles.tabContent}>
      <View style={styles.summaryRow}>
        <View style={styles.summaryCard}>
          <Text style={[styles.summaryValue, { color: (wasteAnalysis?.cancellation_rate || 0) > 10 ? '#EF4444' : '#10B981' }]}>
            {wasteAnalysis?.cancellation_rate || 0}%
          </Text>
          <Text style={styles.summaryLabel}>Cancellation Rate</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>₹{wasteAnalysis?.wasted_revenue || 0}</Text>
          <Text style={styles.summaryLabel}>Wasted Revenue</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>{wasteAnalysis?.cancelled_orders || 0}</Text>
          <Text style={styles.summaryLabel}>Cancelled</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>♻️ Waste Analysis</Text>
        <View style={styles.wasteMetric}>
          <Text style={styles.wasteLabel}>Total Orders (90 days)</Text>
          <Text style={styles.wasteValue}>{wasteAnalysis?.total_orders || 0}</Text>
        </View>
        <View style={styles.wasteMetric}>
          <Text style={styles.wasteLabel}>Cancelled Orders</Text>
          <Text style={[styles.wasteValue, { color: '#EF4444' }]}>{wasteAnalysis?.cancelled_orders || 0}</Text>
        </View>
        <View style={styles.wasteMetric}>
          <Text style={styles.wasteLabel}>Daily Waste Avg</Text>
          <Text style={styles.wasteValue}>₹{wasteAnalysis?.daily_waste_average || 0}</Text>
        </View>
      </View>

      {wasteAnalysis?.wasted_items?.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>🗑️ Most Wasted Items</Text>
          {wasteAnalysis.wasted_items.map((item: any, index: number) => (
            <View key={index} style={styles.wasteItemRow}>
              <Text style={styles.wasteItemName}>{item.name}</Text>
              <Text style={styles.wasteItemCount}>{item.cancelled_count}x cancelled</Text>
            </View>
          ))}
        </View>
      )}

      {/* Revenue Trends */}
      {revenueTrends?.summary && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>💰 Revenue Summary</Text>
          <View style={styles.revenueRow}>
            <Text style={styles.revenueLabel}>Daily Average</Text>
            <Text style={styles.revenueValue}>₹{revenueTrends.summary.daily_average_revenue}</Text>
          </View>
          <View style={styles.revenueRow}>
            <Text style={styles.revenueLabel}>Weekly Average</Text>
            <Text style={styles.revenueValue}>₹{revenueTrends.summary.weekly_average_revenue}</Text>
          </View>
          <View style={styles.revenueRow}>
            <Text style={styles.revenueLabel}>Monthly Average</Text>
            <Text style={styles.revenueValue}>₹{revenueTrends.summary.monthly_average_revenue}</Text>
          </View>
          <View style={styles.revenueRow}>
            <Text style={styles.revenueLabel}>Weekly Growth</Text>
            <Text style={[styles.revenueValue, { color: (revenueTrends.summary.weekly_growth || 0) >= 0 ? '#10B981' : '#EF4444' }]}>
              {revenueTrends.summary.weekly_growth}%
            </Text>
          </View>
          <View style={styles.revenueRow}>
            <Text style={styles.revenueLabel}>All-Time Revenue</Text>
            <Text style={[styles.revenueValue, { color: '#10B981', fontSize: 18 }]}>₹{revenueTrends.summary.total_revenue_all_time}</Text>
          </View>
        </View>
      )}
    </ScrollView>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading analytics...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📊 Analytics</Text>
        <Text style={styles.headerSubtitle}>Data-driven insights for {user?.vendor_name}</Text>
      </View>

      <View style={styles.tabContainer}>
        <TouchableOpacity style={[styles.tab, activeTab === 'daily' && styles.activeTab]} onPress={() => setActiveTab('daily')}>
          <Text style={[styles.tabText, activeTab === 'daily' && styles.activeTabText]}>📅 Daily</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'weekly' && styles.activeTab]} onPress={() => setActiveTab('weekly')}>
          <Text style={[styles.tabText, activeTab === 'weekly' && styles.activeTabText]}>📈 Weekly</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'monthly' && styles.activeTab]} onPress={() => setActiveTab('monthly')}>
          <Text style={[styles.tabText, activeTab === 'monthly' && styles.activeTabText]}>📊 Monthly</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'items' && styles.activeTab]} onPress={() => setActiveTab('items')}>
          <Text style={[styles.tabText, activeTab === 'items' && styles.activeTabText]}>🔥 Items</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'peak' && styles.activeTab]} onPress={() => setActiveTab('peak')}>
          <Text style={[styles.tabText, activeTab === 'peak' && styles.activeTabText]}>⏰ Peak</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'waste' && styles.activeTab]} onPress={() => setActiveTab('waste')}>
          <Text style={[styles.tabText, activeTab === 'waste' && styles.activeTabText]}>♻️ Waste</Text>
        </TouchableOpacity>
      </View>

      {activeTab === 'daily' && renderDailyTab()}
      {activeTab === 'weekly' && renderWeeklyTab()}
      {activeTab === 'monthly' && renderMonthlyTab()}
      {activeTab === 'items' && renderItemsTab()}
      {activeTab === 'peak' && renderPeakTab()}
      {activeTab === 'waste' && renderWasteTab()}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { fontSize: 16, color: '#6B7280' },
  header: { padding: 20, paddingTop: 60, backgroundColor: '#10B981' },
  headerTitle: { fontSize: 24, fontWeight: 'bold', color: 'white' },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.8)', marginTop: 4 },
  tabContainer: { flexDirection: 'row', paddingHorizontal: 12, paddingVertical: 10, gap: 3, backgroundColor: 'white', borderBottomWidth: 1, borderBottomColor: '#E5E7EB', flexWrap: 'wrap' },
  tab: { paddingVertical: 6, paddingHorizontal: 10, borderRadius: 8, backgroundColor: '#F3F5F9', alignItems: 'center' },
  activeTab: { backgroundColor: '#10B981' },
  tabText: { fontSize: 11, fontWeight: '600', color: '#6B7280' },
  activeTabText: { color: 'white' },
  tabContent: { padding: 16 },
  summaryRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  summaryCard: { flex: 1, backgroundColor: 'white', borderRadius: 12, padding: 16, alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  summaryValue: { fontSize: 20, fontWeight: 'bold', color: '#10B981' },
  summaryLabel: { fontSize: 11, color: '#6B7280', marginTop: 4, textAlign: 'center' },
  card: { backgroundColor: 'white', borderRadius: 12, padding: 16, marginBottom: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  cardTitle: { fontSize: 16, fontWeight: 'bold', color: '#111827', marginBottom: 4 },
  cardSubtitle: { fontSize: 12, color: '#6B7280', marginBottom: 12 },
  chartContainer: { flexDirection: 'row', alignItems: 'flex-end', height: 120, gap: 4, paddingTop: 8 },
  chartBar: { flex: 1, alignItems: 'center', justifyContent: 'flex-end' },
  bar: { width: '100%', borderRadius: 4, minHeight: 4 },
  barLabel: { fontSize: 9, color: '#6B7280', marginTop: 4 },
  dataRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  dataDate: { fontSize: 13, color: '#374151', flex: 1 },
  dataOrders: { fontSize: 13, color: '#6B7280', flex: 1, textAlign: 'center' },
  dataRevenue: { fontSize: 13, fontWeight: '600', color: '#10B981', flex: 1, textAlign: 'right' },
  exportButton: { backgroundColor: '#3B82F6', borderRadius: 12, padding: 16, alignItems: 'center', marginBottom: 16 },
  exportButtonText: { color: 'white', fontSize: 16, fontWeight: '600' },
  itemRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  rankBadge: { width: 28, height: 28, borderRadius: 14, backgroundColor: '#FEF3C7', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  rankText: { fontSize: 12, fontWeight: 'bold', color: '#D97706' },
  itemInfo: { flex: 1 },
  itemName: { fontSize: 14, fontWeight: '600', color: '#111827' },
  itemStats: { fontSize: 11, color: '#6B7280', marginTop: 2 },
  itemRevenue: { alignItems: 'flex-end' },
  itemRevenueText: { fontSize: 14, fontWeight: 'bold', color: '#10B981' },
  itemPercentage: { fontSize: 11, color: '#6B7280' },
  peakChart: { marginTop: 8 },
  peakRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  peakHour: { fontSize: 11, fontWeight: '600', color: '#374151', width: 40 },
  peakBar: { height: 20, borderRadius: 4, justifyContent: 'center', paddingHorizontal: 6, minWidth: 30 },
  peakBarText: { color: 'white', fontSize: 10, fontWeight: '600' },
  peakPeriodRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  peakPeriodLabel: { fontSize: 14, color: '#374151', fontWeight: '500' },
  peakPeriodOrders: { fontSize: 14, color: '#F59E0B', fontWeight: '600' },
  wasteMetric: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#E5E7EB' },
  wasteLabel: { fontSize: 14, color: '#374151' },
  wasteValue: { fontSize: 16, fontWeight: 'bold', color: '#111827' },
  wasteItemRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  wasteItemName: { fontSize: 14, color: '#374151' },
  wasteItemCount: { fontSize: 14, color: '#EF4444', fontWeight: '600' },
  revenueRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  revenueLabel: { fontSize: 14, color: '#6B7280' },
  revenueValue: { fontSize: 16, fontWeight: 'bold', color: '#111827' },
});