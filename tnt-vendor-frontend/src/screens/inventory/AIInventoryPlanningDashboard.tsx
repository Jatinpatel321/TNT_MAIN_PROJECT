import React, {useCallback, useEffect, useState} from 'react';
import {
  ActivityIndicator,
  Dimensions,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import {LineChart, BarChart} from 'react-native-chart-kit';
import {vendorApi} from '../../services/vendorApi';

const screenWidth = Dimensions.get('window').width;

type TabType = 'overview' | 'restock' | 'waste' | 'purchase';

export default function AIInventoryPlanningDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<any>(null);

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

  useEffect(() => {
    loadPlan();
  }, [loadPlan]);

  const onRefresh = () => {
    setRefreshing(true);
    loadPlan(true);
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return '#EF4444';
      case 'high': return '#F97316';
      case 'medium': return '#F59E0B';
      case 'low': return '#10B981';
      default: return '#6B7280';
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high': return '#EF4444';
      case 'medium': return '#F59E0B';
      case 'low': return '#10B981';
      default: return '#6B7280';
    }
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#10B981" />
        <Text style={styles.loadingText}>Generating AI inventory plan...</Text>
      </View>
    );
  }

  const summary = plan?.summary || {};
  const itemsFinishing = plan?.items_likely_to_finish || [];
  const itemsRestock = plan?.items_to_restock || [];
  const demand = plan?.expected_demand || {};
  const wastage = plan?.expected_wastage || {};
  const restockSuggestions = plan?.restock_suggestions || [];
  const wasteSuggestions = plan?.waste_reduction_suggestions || [];
  const purchasePlan = plan?.smart_purchase_plan || [];
  const insights = plan?.insights || [];

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
      <View style={styles.header}>
        <Text style={styles.title}>AI Inventory Planning</Text>
        <Text style={styles.subtitle}>Smart predictions for optimal stock management</Text>
      </View>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={() => loadPlan()}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Summary Cards */}
      <View style={styles.summaryGrid}>
        <SummaryCard
          label="Total Items"
          value={summary.total_items || 0}
          icon="📦"
          color="#3B82F6"
        />
        <SummaryCard
          label="Low Stock"
          value={summary.low_stock || 0}
          icon="⚠️"
          color={getPriorityColor((summary.low_stock || 0) > 0 ? 'high' : 'low')}
        />
        <SummaryCard
          label="Out of Stock"
          value={summary.out_of_stock || 0}
          icon="🚫"
          color={getPriorityColor((summary.out_of_stock || 0) > 0 ? 'critical' : 'low')}
        />
        <SummaryCard
          label="Waste Risk"
          value={summary.items_with_waste_risk || 0}
          icon="♻️"
          color={getRiskColor((summary.items_with_waste_risk || 0) > 0 ? 'high' : 'low')}
        />
        <SummaryCard
          label="To Restock"
          value={summary.items_to_restock || 0}
          icon="🔄"
          color={getPriorityColor((summary.items_to_restock || 0) > 0 ? 'medium' : 'low')}
        />
        <SummaryCard
          label="At Risk"
          value={summary.items_likely_to_finish || 0}
          icon="⏰"
          color={getPriorityColor((summary.items_likely_to_finish || 0) > 0 ? 'critical' : 'low')}
        />
      </View>

      {/* Tab Selector */}
      <View style={styles.tabContainer}>
        {(['overview', 'restock', 'waste', 'purchase'] as TabType[]).map(tab => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, activeTab === tab && styles.activeTab]}
            onPress={() => setActiveTab(tab)}>
            <Text style={[styles.tabText, activeTab === tab && styles.activeTabText]}>
              {tab.toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <View style={styles.section}>
          {/* Items Likely to Finish */}
          {itemsFinishing.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>⏰ Items Likely to Finish</Text>
              {itemsFinishing.slice(0, 5).map((item: any, index: number) => (
                <View key={index} style={styles.itemRow}>
                  <View style={styles.itemInfo}>
                    <Text style={styles.itemName}>{item.item_name}</Text>
                    <Text style={styles.itemDetail}>
                      Stock: {item.current_stock} | Demand: {item.daily_demand}/day
                    </Text>
                  </View>
                  <View style={styles.itemStatus}>
                    <View style={[styles.severityBadge, {backgroundColor: getPriorityColor(item.severity)}]}>
                      <Text style={styles.severityText}>{item.severity.toUpperCase()}</Text>
                    </View>
                    <Text style={styles.itemDays}>{item.days_until_out}d left</Text>
                  </View>
                </View>
              ))}
            </View>
          )}

          {/* Expected Demand */}
          {demand.items && demand.items.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>📊 Expected Demand</Text>
              <View style={styles.demandHeader}>
                <Text style={styles.demandTotal}>
                  Daily: {demand.total_daily_demand} | Weekly: {demand.total_weekly_demand}
                </Text>
              </View>
              {demand.items.slice(0, 5).map((item: any, index: number) => (
                <View key={index} style={styles.itemRow}>
                  <Text style={styles.itemName}>{item.item_name}</Text>
                  <Text style={styles.itemDetail}>
                    Daily: {item.daily} | Weekly: {item.weekly}
                  </Text>
                </View>
              ))}
            </View>
          )}

          {/* Waste Risk */}
          {wastage.items && wastage.items.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>♻️ Waste Risk</Text>
              {wastage.items.slice(0, 3).map((item: any, index: number) => (
                <View key={index} style={styles.itemRow}>
                  <Text style={styles.itemName}>{item.item_name}</Text>
                  <View style={styles.itemStatus}>
                    <Text style={[styles.wasteValue, {color: getRiskColor(item.waste_risk)}]}>
                      {item.predicted_wastage} units
                    </Text>
                    <View style={[styles.riskBadge, {backgroundColor: getRiskColor(item.waste_risk)}]}>
                      <Text style={styles.riskText}>{item.waste_risk.toUpperCase()}</Text>
                    </View>
                  </View>
                </View>
              ))}
            </View>
          )}

          {/* Insights */}
          {insights.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>💡 AI Insights</Text>
              {insights.map((insight: string, index: number) => (
                <View key={index} style={styles.insightRow}>
                  <Text style={styles.insightBullet}>•</Text>
                  <Text style={styles.insightText}>{insight}</Text>
                </View>
              ))}
            </View>
          )}
        </View>
      )}

      {/* Restock Tab */}
      {activeTab === 'restock' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Restock Suggestions</Text>

          {restockSuggestions.length > 0 ? (
            restockSuggestions.map((suggestion: any, index: number) => (
              <View key={index} style={styles.suggestionCard}>
                <View style={styles.suggestionHeader}>
                  <Text style={styles.suggestionName}>{suggestion.item_name}</Text>
                  <View style={[styles.priorityBadge, {backgroundColor: getPriorityColor(suggestion.priority)}]}>
                    <Text style={styles.priorityText}>{suggestion.priority.toUpperCase()}</Text>
                  </View>
                </View>
                <View style={styles.suggestionDetails}>
                  <Text style={styles.suggestionDetail}>Current Stock: {suggestion.current_stock}</Text>
                  <Text style={styles.suggestionDetail}>Suggested: {suggestion.suggested_quantity} units</Text>
                  {suggestion.restock_by && (
                    <Text style={styles.suggestionDetail}>Restock By: {suggestion.restock_by}</Text>
                  )}
                </View>
                <Text style={styles.suggestionReason}>{suggestion.reason}</Text>
                <Text style={styles.suggestionAction}>{suggestion.action}</Text>
              </View>
            ))
          ) : (
            <View style={styles.emptyCard}>
              <Text style={styles.emptyText}>No restock suggestions - all items adequately stocked</Text>
            </View>
          )}
        </View>
      )}

      {/* Waste Tab */}
      {activeTab === 'waste' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Waste Reduction</Text>

          {wasteSuggestions.map((suggestion: any, index: number) => (
            <View key={index} style={[styles.suggestionCard, {borderLeftColor: getRiskColor(suggestion.severity)}]}>
              <View style={styles.suggestionHeader}>
                <Text style={styles.suggestionType}>{suggestion.type.replace('_', ' ').toUpperCase()}</Text>
                <View style={[styles.severityBadge, {backgroundColor: getRiskColor(suggestion.severity)}]}>
                  <Text style={styles.severityText}>{suggestion.severity.toUpperCase()}</Text>
                </View>
              </View>
              <Text style={styles.suggestionText}>{suggestion.suggestion}</Text>
              <Text style={styles.suggestionAction}>→ {suggestion.action}</Text>
              {suggestion.estimated_savings && (
                <Text style={styles.savingsText}>💰 {suggestion.estimated_savings}</Text>
              )}
            </View>
          ))}
        </View>
      )}

      {/* Purchase Plan Tab */}
      {activeTab === 'purchase' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Smart Purchase Plan</Text>
          
          {plan?.total_estimated_cost > 0 && (
            <View style={styles.totalCostCard}>
              <Text style={styles.totalCostLabel}>Estimated Total Cost</Text>
              <Text style={styles.totalCostValue}>${plan.total_estimated_cost}</Text>
            </View>
          )}

          {purchasePlan.map((item: any, index: number) => (
            <View key={index} style={styles.purchaseCard}>
              <View style={styles.purchaseHeader}>
                <Text style={styles.purchaseName}>{item.item_name}</Text>
                <View style={[styles.priorityBadge, {backgroundColor: getPriorityColor(item.priority)}]}>
                  <Text style={styles.priorityText}>{item.priority.toUpperCase()}</Text>
                </View>
              </View>
              <View style={styles.purchaseDetails}>
                <View style={styles.purchaseRow}>
                  <Text style={styles.purchaseLabel}>Current Stock</Text>
                  <Text style={styles.purchaseValue}>{item.current_stock}</Text>
                </View>
                <View style={styles.purchaseRow}>
                  <Text style={styles.purchaseLabel}>Daily Demand</Text>
                  <Text style={styles.purchaseValue}>{item.daily_demand}</Text>
                </View>
                <View style={styles.purchaseRow}>
                  <Text style={styles.purchaseLabel}>Optimal Quantity</Text>
                  <Text style={[styles.purchaseValue, styles.optimalValue]}>{item.optimal_quantity}</Text>
                </View>
                <View style={styles.purchaseRow}>
                  <Text style={styles.purchaseLabel}>Days to Cover</Text>
                  <Text style={styles.purchaseValue}>{item.days_to_cover}d</Text>
                </View>
                <View style={styles.purchaseRow}>
                  <Text style={styles.purchaseLabel}>Delivery Window</Text>
                  <Text style={styles.purchaseValue}>{item.expected_delivery_window}</Text>
                </View>
                {item.estimated_cost && (
                  <View style={styles.purchaseRow}>
                    <Text style={styles.purchaseLabel}>Estimated Cost</Text>
                    <Text style={styles.purchaseValue}>${item.estimated_cost.total_cost}</Text>
                  </View>
                )}
              </View>
              <Text style={styles.suggestedVendor}>🏪 {item.suggested_vendor}</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

// ── Helper Components ────────────────────────────────────────────────────

function SummaryCard({label, value, icon, color}: any) {
  return (
    <View style={[styles.summaryCard, {borderLeftColor: color}]}>
      <Text style={styles.summaryIcon}>{icon}</Text>
      <Text style={[styles.summaryValue, {color}]}>{value}</Text>
      <Text style={styles.summaryLabel}>{label}</Text>
    </View>
  );
}

// ── Chart Configuration ──────────────────────────────────────────────────

const chartConfig = {
  backgroundColor: '#1F2937',
  backgroundGradientFrom: '#1F2937',
  backgroundGradientTo: '#1F2937',
  decimalPlaces: 0,
  color: (opacity = 1) => `rgba(16, 185, 129, ${opacity})`,
  labelColor: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
  style: {borderRadius: 16},
};

// ── Styles ───────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#111827'},
  centered: {flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#111827'},
  loadingText: {marginTop: 12, fontSize: 16, color: '#9CA3AF'},
  header: {padding: 20, paddingTop: 40},
  title: {fontSize: 28, fontWeight: 'bold', color: '#F9FAFB', marginBottom: 4},
  subtitle: {fontSize: 14, color: '#9CA3AF'},
  errorBox: {margin: 16, padding: 16, backgroundColor: '#7F1D1D', borderRadius: 8, borderWidth: 1, borderColor: '#EF4444'},
  errorText: {color: '#FCA5A5', fontSize: 14, marginBottom: 8},
  retryText: {color: '#F9FAFB', fontSize: 14, fontWeight: '600'},

  summaryGrid: {flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: 16, marginBottom: 16, gap: 12},
  summaryCard: {flex: 1, minWidth: '45%', backgroundColor: '#1F2937', borderRadius: 12, padding: 16, borderLeftWidth: 4},
  summaryIcon: {fontSize: 24, marginBottom: 8},
  summaryValue: {fontSize: 24, fontWeight: 'bold', marginBottom: 4},
  summaryLabel: {fontSize: 12, color: '#9CA3AF'},

  tabContainer: {flexDirection: 'row', marginHorizontal: 16, marginBottom: 16, backgroundColor: '#1F2937', borderRadius: 8, padding: 4},
  tab: {flex: 1, paddingVertical: 8, paddingHorizontal: 12, borderRadius: 6, alignItems: 'center'},
  activeTab: {backgroundColor: '#10B981'},
  tabText: {fontSize: 12, fontWeight: '600', color: '#9CA3AF'},
  activeTabText: {color: '#FFFFFF'},

  section: {marginBottom: 24},
  sectionTitle: {fontSize: 20, fontWeight: '600', color: '#F9FAFB', marginHorizontal: 16, marginBottom: 12},

  card: {marginHorizontal: 16, marginBottom: 16, backgroundColor: '#1F2937', borderRadius: 12, padding: 16},
  cardTitle: {fontSize: 16, fontWeight: '600', color: '#F9FAFB', marginBottom: 12},

  itemRow: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#374151'},
  itemInfo: {flex: 1},
  itemName: {fontSize: 14, fontWeight: '600', color: '#F9FAFB', marginBottom: 2},
  itemDetail: {fontSize: 12, color: '#9CA3AF'},
  itemStatus: {alignItems: 'flex-end'},
  itemDays: {fontSize: 12, color: '#EF4444', marginTop: 4},

  severityBadge: {paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4},
  severityText: {fontSize: 10, fontWeight: 'bold', color: '#FFFFFF'},
  riskBadge: {paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, marginTop: 4},
  riskText: {fontSize: 10, fontWeight: 'bold', color: '#FFFFFF'},

  demandHeader: {marginBottom: 12},
  demandTotal: {fontSize: 14, color: '#10B981', fontWeight: '600'},
  wasteValue: {fontSize: 14, fontWeight: '600', marginBottom: 4},

  insightRow: {flexDirection: 'row', marginBottom: 8},
  insightBullet: {color: '#10B981', marginRight: 8, fontSize: 16},
  insightText: {flex: 1, fontSize: 14, color: '#D1D5DB', lineHeight: 20},

  suggestionCard: {marginHorizontal: 16, marginBottom: 16, backgroundColor: '#1F2937', borderRadius: 12, padding: 16, borderLeftWidth: 4, borderLeftColor: '#10B981'},
  suggestionHeader: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8},
  suggestionName: {fontSize: 16, fontWeight: '600', color: '#F9FAFB', flex: 1},
  suggestionType: {fontSize: 12, fontWeight: '600', color: '#9CA3AF'},
  suggestionDetails: {marginBottom: 8},
  suggestionDetail: {fontSize: 14, color: '#D1D5DB', marginBottom: 2},
  suggestionReason: {fontSize: 12, color: '#F59E0B', marginBottom: 4},
  suggestionAction: {fontSize: 12, color: '#10B981', fontWeight: '600', marginTop: 4},
  suggestionText: {fontSize: 14, color: '#D1D5DB', marginBottom: 8, lineHeight: 20},

  priorityBadge: {paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4, marginLeft: 8},
  priorityText: {fontSize: 10, fontWeight: 'bold', color: '#FFFFFF'},
  savingsText: {fontSize: 12, color: '#10B981', marginTop: 8},

  totalCostCard: {marginHorizontal: 16, marginBottom: 16, backgroundColor: '#1F2937', borderRadius: 12, padding: 20, alignItems: 'center'},
  totalCostLabel: {fontSize: 14, color: '#9CA3AF', marginBottom: 4},
  totalCostValue: {fontSize: 32, fontWeight: 'bold', color: '#10B981'},

  purchaseCard: {marginHorizontal: 16, marginBottom: 16, backgroundColor: '#1F2937', borderRadius: 12, padding: 16},
  purchaseHeader: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12},
  purchaseName: {fontSize: 16, fontWeight: '600', color: '#F9FAFB', flex: 1},
  purchaseDetails: {marginBottom: 8},
  purchaseRow: {flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#374151'},
  purchaseLabel: {fontSize: 14, color: '#9CA3AF'},
  purchaseValue: {fontSize: 14, fontWeight: '600', color: '#F9FAFB'},
  optimalValue: {color: '#10B981'},
  suggestedVendor: {fontSize: 12, color: '#3B82F6', marginTop: 8},

  emptyCard: {marginHorizontal: 16, marginBottom: 16, backgroundColor: '#1F2937', borderRadius: 12, padding: 32, alignItems: 'center'},
  emptyText: {fontSize: 14, color: '#9CA3AF'},
});
