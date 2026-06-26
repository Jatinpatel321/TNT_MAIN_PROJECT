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

type TabType = 'overview' | 'score' | 'history' | 'insights';

export default function PerformanceIntelligenceDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<any>(null);
  const [score, setScore] = useState<any>(null);
  const [history, setHistory] = useState<any>(null);
  const [insights, setInsights] = useState<any>(null);

  const loadData = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      setError(null);

      // Load all data in parallel
      const [metricsRes, scoreRes, historyRes, insightsRes] = await Promise.all([
        vendorApi.getPerformanceMetrics(),
        vendorApi.getVendorScore(),
        vendorApi.getPerformanceHistory(),
        vendorApi.getDashboardInsights(),
      ]);

      setMetrics(metricsRes.data);
      setScore(scoreRes.data);
      setHistory(historyRes.data);
      setInsights(insightsRes.data);
    } catch (err: any) {
      setError(err?.message || 'Unable to load performance data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onRefresh = () => {
    setRefreshing(true);
    loadData(true);
  };

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'excellent': return '#10B981';
      case 'good': return '#3B82F6';
      case 'fair': return '#F59E0B';
      case 'poor': return '#EF4444';
      default: return '#6B7280';
    }
  };

  const getMetricColor = (value: number, thresholds: {good: number; fair: number}) => {
    if (value >= thresholds.good) return '#10B981';
    if (value >= thresholds.fair) return '#F59E0B';
    return '#EF4444';
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#10B981" />
        <Text style={styles.loadingText}>Loading performance data...</Text>
      </View>
    );
  }

  const m = metrics?.metrics || {};
  const grade = score?.performance_grade || 'fair';
  const gradeColor = getGradeColor(grade);

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
      <View style={styles.header}>
        <Text style={styles.title}>Performance Intelligence</Text>
        <Text style={styles.subtitle}>AI-powered vendor performance analytics</Text>
      </View>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={() => loadData()}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Vendor Score Card */}
      {score && (
        <View style={[styles.scoreCard, {borderLeftColor: gradeColor}]}>
          <View style={styles.scoreHeader}>
            <View>
              <Text style={styles.scoreLabel}>Vendor Score</Text>
              <Text style={[styles.scoreValue, {color: gradeColor}]}>
                {score.vendor_score}/100
              </Text>
            </View>
            <View style={[styles.gradeBadge, {backgroundColor: gradeColor}]}>
              <Text style={styles.gradeIcon}>{score.icon}</Text>
              <Text style={styles.gradeText}>{grade.toUpperCase()}</Text>
            </View>
          </View>
          <Text style={styles.gradeDescription}>{score.grade_description}</Text>
        </View>
      )}

      {/* Tab Selector */}
      <View style={styles.tabContainer}>
        {(['overview', 'score', 'history', 'insights'] as TabType[]).map(tab => (
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
          <Text style={styles.sectionTitle}>Performance Overview</Text>

          {/* Key Metrics Grid */}
          <View style={styles.metricsGrid}>
            <MetricCard
              label="Prep Speed"
              value={`${m.preparation_speed || 0} min`}
              icon="⚡"
              color={getMetricColor(m.preparation_speed || 0, {good: 20, fair: 35})}
            />
            <MetricCard
              label="Completion"
              value={`${m.completion_rate || 0}%`}
              icon="✓"
              color={getMetricColor(m.completion_rate || 0, {good: 85, fair: 70})}
            />
            <MetricCard
              label="Cancellation"
              value={`${m.cancellation_rate || 0}%`}
              icon="✗"
              color={getMetricColor(100 - (m.cancellation_rate || 0), {good: 90, fair: 80})}
            />
            <MetricCard
              label="Satisfaction"
              value={`${m.customer_satisfaction || 0}/100`}
              icon="😊"
              color={getMetricColor(m.customer_satisfaction || 0, {good: 80, fair: 60})}
            />
            <MetricCard
              label="Accuracy"
              value={`${m.order_accuracy || 0}%`}
              icon="🎯"
              color={getMetricColor(m.order_accuracy || 0, {good: 95, fair: 85})}
            />
            <MetricCard
              label="Avg Delay"
              value={`${m.average_delay || 0} min`}
              icon="⏱️"
              color={getMetricColor(30 - (m.average_delay || 0), {good: 20, fair: 10})}
            />
          </View>

          {/* Performance Breakdown */}
          {metrics?.breakdown && (
            <View style={styles.breakdownCard}>
              <Text style={styles.breakdownTitle}>Order Breakdown</Text>
              <View style={styles.breakdownRow}>
                <View style={styles.breakdownItem}>
                  <Text style={styles.breakdownValue}>{metrics.breakdown.total_orders}</Text>
                  <Text style={styles.breakdownLabel}>Total Orders</Text>
                </View>
                <View style={styles.breakdownItem}>
                  <Text style={[styles.breakdownValue, {color: '#10B981'}]}>
                    {metrics.breakdown.completed_orders}
                  </Text>
                  <Text style={styles.breakdownLabel}>Completed</Text>
                </View>
                <View style={styles.breakdownItem}>
                  <Text style={[styles.breakdownValue, {color: '#EF4444'}]}>
                    {metrics.breakdown.cancelled_orders}
                  </Text>
                  <Text style={styles.breakdownLabel}>Cancelled</Text>
                </View>
                <View style={styles.breakdownItem}>
                  <Text style={styles.breakdownValue}>${metrics.breakdown.total_revenue}</Text>
                  <Text style={styles.breakdownLabel}>Revenue</Text>
                </View>
              </View>
            </View>
          )}

          {/* Insights */}
          {metrics?.insights && metrics.insights.length > 0 && (
            <View style={styles.insightsCard}>
              <Text style={styles.insightsTitle}>AI Insights</Text>
              {metrics.insights.slice(0, 5).map((insight: string, index: number) => (
                <View key={index} style={styles.insightItem}>
                  <Text style={styles.insightBullet}>•</Text>
                  <Text style={styles.insightText}>{insight}</Text>
                </View>
              ))}
            </View>
          )}
        </View>
      )}

      {/* Score Tab */}
      {activeTab === 'score' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Vendor Score Details</Text>

          {/* Score Components */}
          <View style={styles.scoreComponentsCard}>
            <Text style={styles.cardTitle}>Score Components</Text>
            <View style={styles.componentRow}>
              <Text style={styles.componentLabel}>Completion Rate</Text>
              <View style={styles.componentBar}>
                <View
                  style={[
                    styles.componentFill,
                    {
                      width: `${m.completion_rate || 0}%`,
                      backgroundColor: getMetricColor(m.completion_rate || 0, {good: 85, fair: 70}),
                    },
                  ]}
                />
              </View>
              <Text style={styles.componentValue}>{m.completion_rate?.toFixed(1)}%</Text>
            </View>
            <View style={styles.componentRow}>
              <Text style={styles.componentLabel}>Cancellation (inverse)</Text>
              <View style={styles.componentBar}>
                <View
                  style={[
                    styles.componentFill,
                    {
                      width: `${100 - (m.cancellation_rate || 0)}%`,
                      backgroundColor: getMetricColor(100 - (m.cancellation_rate || 0), {good: 90, fair: 80}),
                    },
                  ]}
                />
              </View>
              <Text style={styles.componentValue}>{(100 - (m.cancellation_rate || 0)).toFixed(1)}%</Text>
            </View>
            <View style={styles.componentRow}>
              <Text style={styles.componentLabel}>Customer Satisfaction</Text>
              <View style={styles.componentBar}>
                <View
                  style={[
                    styles.componentFill,
                    {
                      width: `${m.customer_satisfaction || 0}%`,
                      backgroundColor: getMetricColor(m.customer_satisfaction || 0, {good: 80, fair: 60}),
                    },
                  ]}
                />
              </View>
              <Text style={styles.componentValue}>{m.customer_satisfaction?.toFixed(1)}</Text>
            </View>
            <View style={styles.componentRow}>
              <Text style={styles.componentLabel}>Order Accuracy</Text>
              <View style={styles.componentBar}>
                <View
                  style={[
                    styles.componentFill,
                    {
                      width: `${m.order_accuracy || 0}%`,
                      backgroundColor: getMetricColor(m.order_accuracy || 0, {good: 95, fair: 85}),
                    },
                  ]}
                />
              </View>
              <Text style={styles.componentValue}>{m.order_accuracy?.toFixed(1)}%</Text>
            </View>
            <View style={styles.componentRow}>
              <Text style={styles.componentLabel}>Preparation Speed</Text>
              <View style={styles.componentBar}>
                <View
                  style={[
                    styles.componentFill,
                    {
                      width: `${Math.max(0, Math.min(100, (60 - (m.preparation_speed || 0)) / 30 * 100))}%`,
                      backgroundColor: getMetricColor(m.preparation_speed || 0, {good: 20, fair: 35}),
                    },
                  ]}
                />
              </View>
              <Text style={styles.componentValue}>{m.preparation_speed?.toFixed(1)} min</Text>
            </View>
            <View style={styles.componentRow}>
              <Text style={styles.componentLabel}>Average Delay</Text>
              <View style={styles.componentBar}>
                <View
                  style={[
                    styles.componentFill,
                    {
                      width: `${Math.max(0, Math.min(100, (30 - (m.average_delay || 0)) / 20 * 100))}%`,
                      backgroundColor: getMetricColor(30 - (m.average_delay || 0), {good: 20, fair: 10}),
                    },
                  ]}
                />
              </View>
              <Text style={styles.componentValue}>{m.average_delay?.toFixed(1)} min</Text>
            </View>
          </View>

          {/* Grade Distribution */}
          <View style={styles.gradeInfoCard}>
            <Text style={styles.cardTitle}>Grade Thresholds</Text>
            <View style={styles.gradeRow}>
              <View style={[styles.gradeItem, {backgroundColor: '#10B981'}]}>
                <Text style={styles.gradeLabel}>Excellent</Text>
                <Text style={styles.gradeThreshold}>≥85</Text>
              </View>
              <View style={[styles.gradeItem, {backgroundColor: '#3B82F6'}]}>
                <Text style={styles.gradeLabel}>Good</Text>
                <Text style={styles.gradeThreshold}>≥70</Text>
              </View>
              <View style={[styles.gradeItem, {backgroundColor: '#F59E0B'}]}>
                <Text style={styles.gradeLabel}>Fair</Text>
                <Text style={styles.gradeThreshold}>≥50</Text>
              </View>
              <View style={[styles.gradeItem, {backgroundColor: '#EF4444'}]}>
                <Text style={styles.gradeLabel}>Poor</Text>
                <Text style={styles.gradeThreshold}><50</Text>
              </View>
            </View>
          </View>
        </View>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Performance History</Text>

          {history?.history && history.history.length > 0 ? (
            <>
              {/* Score Trend Chart */}
              <View style={styles.chartCard}>
                <Text style={styles.chartTitle}>Vendor Score Trend</Text>
                <LineChart
                  data={{
                    labels: history.history.slice(0, 10).reverse().map((h: any) => 
                      new Date(h.metric_date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'})
                    ),
                    datasets: [
                      {
                        data: history.history.slice(0, 10).reverse().map((h: any) => h.vendor_score),
                        color: (opacity = 1) => `rgba(16, 185, 129, ${opacity})`,
                        strokeWidth: 2,
                      },
                    ],
                  }}
                  width={screenWidth - 40}
                  height={220}
                  chartConfig={chartConfig}
                  bezier
                  style={styles.chart}
                />
              </View>

              {/* History List */}
              <View style={styles.historyCard}>
                <Text style={styles.cardTitle}>Recent Records</Text>
                {history.history.slice(0, 10).map((record: any, index: number) => (
                  <View key={index} style={styles.historyRow}>
                    <View style={styles.historyInfo}>
                      <Text style={styles.historyDate}>
                        {new Date(record.metric_date).toLocaleDateString()}
                      </Text>
                      <Text style={styles.historyScore}>Score: {record.vendor_score}</Text>
                    </View>
                    <View style={styles.historyMetrics}>
                      <Text style={styles.historyMetric}>
                        Prep: {record.preparation_speed}min
                      </Text>
                      <Text style={styles.historyMetric}>
                        Complete: {record.completion_rate}%
                      </Text>
                    </View>
                  </View>
                ))}
              </View>
            </>
          ) : (
            <View style={styles.emptyCard}>
              <Text style={styles.emptyText}>No performance history available yet</Text>
            </View>
          )}
        </View>
      )}

      {/* Insights Tab */}
      {activeTab === 'insights' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>AI Insights & Recommendations</Text>

          {/* Forecast Insights */}
          {insights && (
            <>
              <View style={styles.insightCard}>
                <Text style={styles.insightTitle}>Forecast Adjustments</Text>
                <View style={styles.insightRow}>
                  <Text style={styles.insightLabel}>Completion Rate Factor:</Text>
                  <Text style={styles.insightValue}>
                    {(insights.forecast_adjustments?.completion_rate_factor * 100).toFixed(0)}%
                  </Text>
                </View>
                <View style={styles.insightRow}>
                  <Text style={styles.insightLabel}>Cancellation Risk:</Text>
                  <Text style={styles.insightValue}>
                    {(insights.forecast_adjustments?.cancellation_risk * 100).toFixed(0)}%
                  </Text>
                </View>
                <View style={styles.insightRow}>
                  <Text style={styles.insightLabel}>Reliability Score:</Text>
                  <Text style={styles.insightValue}>
                    {(insights.forecast_adjustments?.reliability_score * 100).toFixed(0)}%
                  </Text>
                </View>
              </View>

              {/* Recommendation Factors */}
              <View style={styles.insightCard}>
                <Text style={styles.insightTitle}>Recommendation Factors</Text>
                <View style={styles.factorRow}>
                  <Text style={styles.factorLabel}>Reliability</Text>
                  <View style={styles.factorBar}>
                    <View
                      style={[
                        styles.factorFill,
                        {
                          width: `${(insights.recommendation_factors?.reliability || 0) * 100}%`,
                          backgroundColor: '#10B981',
                        },
                      ]}
                    />
                  </View>
                </View>
                <View style={styles.factorRow}>
                  <Text style={styles.factorLabel}>Speed</Text>
                  <View style={styles.factorBar}>
                    <View
                      style={[
                        styles.factorFill,
                        {
                          width: `${(insights.recommendation_factors?.speed || 0) * 100}%`,
                          backgroundColor: '#3B82F6',
                        },
                      ]}
                    />
                  </View>
                </View>
                <View style={styles.factorRow}>
                  <Text style={styles.factorLabel}>Quality</Text>
                  <View style={styles.factorBar}>
                    <View
                      style={[
                        styles.factorFill,
                        {
                          width: `${(insights.recommendation_factors?.quality || 0) * 100}%`,
                          backgroundColor: '#8B5CF6',
                        },
                      ]}
                    />
                  </View>
                </View>
                <View style={styles.factorRow}>
                  <Text style={styles.factorLabel}>Satisfaction</Text>
                  <View style={styles.factorBar}>
                    <View
                      style={[
                        styles.factorFill,
                        {
                          width: `${(insights.recommendation_factors?.customer_satisfaction || 0) * 100}%`,
                          backgroundColor: '#F59E0B',
                        },
                      ]}
                    />
                  </View>
                </View>
              </View>

              {/* Priority Areas */}
              {insights.priority_areas && insights.priority_areas.length > 0 && (
                <View style={styles.priorityCard}>
                  <Text style={styles.cardTitle}>Priority Improvement Areas</Text>
                  {insights.priority_areas.map((area: string, index: number) => (
                    <View key={index} style={styles.priorityItem}>
                      <Text style={styles.priorityIcon}>!</Text>
                      <Text style={styles.priorityText}>{area}</Text>
                    </View>
                  ))}
                </View>
              )}

              {/* Suggested Actions */}
              {insights.suggested_actions && insights.suggested_actions.length > 0 && (
                <View style={styles.actionsCard}>
                  <Text style={styles.cardTitle}>Suggested Actions</Text>
                  {insights.suggested_actions.map((action: string, index: number) => (
                    <View key={index} style={styles.actionItem}>
                      <Text style={styles.actionIcon}>→</Text>
                      <Text style={styles.actionText}>{action}</Text>
                    </View>
                  ))}
                </View>
              )}
            </>
          )}
        </View>
      )}
    </ScrollView>
  );
}

// ── Helper Components ────────────────────────────────────────────────────

function MetricCard({label, value, icon, color}: any) {
  return (
    <View style={[styles.metricCard, {borderLeftColor: color}]}>
      <Text style={styles.metricIcon}>{icon}</Text>
      <Text style={[styles.metricValue, {color}]}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
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
  style: {
    borderRadius: 16,
  },
  propsForDots: {
    r: '4',
    strokeWidth: '2',
    stroke: '#10B981',
  },
};

// ── Styles ───────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#111827',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#111827',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#9CA3AF',
  },
  header: {
    padding: 20,
    paddingTop: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#F9FAFB',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  errorBox: {
    margin: 16,
    padding: 16,
    backgroundColor: '#7F1D1D',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#EF4444',
  },
  errorText: {
    color: '#FCA5A5',
    fontSize: 14,
    marginBottom: 8,
  },
  retryText: {
    color: '#F9FAFB',
    fontSize: 14,
    fontWeight: '600',
  },
  scoreCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 20,
    borderLeftWidth: 4,
  },
  scoreHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  scoreLabel: {
    fontSize: 14,
    color: '#9CA3AF',
    marginBottom: 4,
  },
  scoreValue: {
    fontSize: 32,
    fontWeight: 'bold',
  },
  gradeBadge: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: 'center',
  },
  gradeIcon: {
    fontSize: 20,
    marginBottom: 2,
  },
  gradeText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  gradeDescription: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 4,
  },
  tabContainer: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 8,
    padding: 4,
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 6,
    alignItems: 'center',
  },
  activeTab: {
    backgroundColor: '#10B981',
  },
  tabText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#9CA3AF',
  },
  activeTabText: {
    color: '#FFFFFF',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#F9FAFB',
    marginHorizontal: 16,
    marginBottom: 12,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: 16,
    marginBottom: 16,
    gap: 12,
  },
  metricCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 4,
  },
  metricIcon: {
    fontSize: 24,
    marginBottom: 8,
  },
  metricValue: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  metricLabel: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  breakdownCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  breakdownTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#F9FAFB',
    marginBottom: 12,
  },
  breakdownRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  breakdownItem: {
    alignItems: 'center',
  },
  breakdownValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#10B981',
    marginBottom: 4,
  },
  breakdownLabel: {
    fontSize: 11,
    color: '#9CA3AF',
  },
  insightsCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  insightsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#F9FAFB',
    marginBottom: 12,
  },
  insightItem: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  insightBullet: {
    color: '#10B981',
    marginRight: 8,
    fontSize: 16,
  },
  insightText: {
    flex: 1,
    fontSize: 14,
    color: '#D1D5DB',
    lineHeight: 20,
  },
  scoreComponentsCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#F9FAFB',
    marginBottom: 16,
  },
  componentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  componentLabel: {
    fontSize: 13,
    color: '#9CA3AF',
    width: 120,
  },
  componentBar: {
    flex: 1,
    height: 8,
    backgroundColor: '#374151',
    borderRadius: 4,
    overflow: 'hidden',
    marginHorizontal: 8,
  },
  componentFill: {
    height: '100%',
    borderRadius: 4,
  },
  componentValue: {
    fontSize: 13,
    fontWeight: '600',
    color: '#F9FAFB',
    width: 60,
    textAlign: 'right',
  },
  gradeInfoCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  gradeRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 12,
  },
  gradeItem: {
    padding: 8,
    borderRadius: 8,
    alignItems: 'center',
    minWidth: 60,
  },
  gradeLabel: {
    fontSize: 11,
    color: '#FFFFFF',
    marginBottom: 4,
  },
  gradeThreshold: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  chartCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  chartTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F9FAFB',
    marginBottom: 12,
  },
  chart: {
    borderRadius: 16,
  },
  historyCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  historyRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#374151',
  },
  historyInfo: {
    flex: 1,
  },
  historyDate: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F9FAFB',
    marginBottom: 2,
  },
  historyScore: {
    fontSize: 12,
    color: '#10B981',
  },
  historyMetrics: {
    alignItems: 'flex-end',
  },
  historyMetric: {
    fontSize: 12,
    color: '#9CA3AF',
    marginBottom: 2,
  },
  emptyCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 32,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  insightCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  insightTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#F9FAFB',
    marginBottom: 12,
  },
  insightRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#374151',
  },
  insightLabel: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  insightValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#10B981',
  },
  factorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  factorLabel: {
    fontSize: 13,
    color: '#9CA3AF',
    width: 100,
  },
  factorBar: {
    flex: 1,
    height: 6,
    backgroundColor: '#374151',
    borderRadius: 3,
    overflow: 'hidden',
    marginHorizontal: 8,
  },
  factorFill: {
    height: '100%',
    borderRadius: 3,
  },
  priorityCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  priorityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
  },
  priorityIcon: {
    color: '#F59E0B',
    marginRight: 8,
    fontSize: 16,
    fontWeight: 'bold',
  },
  priorityText: {
    flex: 1,
    fontSize: 14,
    color: '#D1D5DB',
  },
  actionsCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  actionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
  },
  actionIcon: {
    color: '#10B981',
    marginRight: 8,
    fontSize: 16,
    fontWeight: 'bold',
  },
  actionText: {
    flex: 1,
    fontSize: 14,
    color: '#D1D5DB',
  },
});
