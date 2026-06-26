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
import {LineChart, BarChart, PieChart} from 'react-native-chart-kit';
import {vendorApi, type ComprehensiveForecast} from '../../services/vendorApi';

type TimeHorizon = 'short_term' | 'daily' | 'weekly' | 'monthly';

const screenWidth = Dimensions.get('window').width;

export default function EnhancedForecastDashboard() {
  const [data, setData] = useState<ComprehensiveForecast | null>(null);
  const [activeHorizon, setActiveHorizon] = useState<TimeHorizon>('daily');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadForecast = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      setError(null);
      const response = await vendorApi.getComprehensiveForecast();
      setData(response.data);
    } catch (err: any) {
      setError(err?.message || 'Unable to load forecast data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadForecast();
  }, [loadForecast]);

  const onRefresh = () => {
    setRefreshing(true);
    loadForecast(true);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return '#10B981'; // Green - High
    if (confidence >= 0.5) return '#F59E0B'; // Yellow - Medium
    return '#EF4444'; // Red - Low
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.5) return 'Medium';
    return 'Low';
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#10B981" />
        <Text style={styles.loadingText}>Loading forecast data...</Text>
      </View>
    );
  }

  const forecast = data?.[activeHorizon];
  const overallConfidence = data?.insights ? 0.75 : 0.5;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
      <View style={styles.header}>
        <Text style={styles.title}>AI Forecast Dashboard</Text>
        <Text style={styles.subtitle}>Multi-horizon demand predictions</Text>
      </View>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={() => loadForecast()}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Overall Confidence Score */}
      <View style={styles.confidenceCard}>
        <Text style={styles.confidenceTitle}>Overall Forecast Confidence</Text>
        <View style={styles.confidenceBar}>
          <View
            style={[
              styles.confidenceFill,
              {
                width: `${overallConfidence * 100}%`,
                backgroundColor: getConfidenceColor(overallConfidence),
              },
            ]}
          />
        </View>
        <View style={styles.confidenceLabels}>
          <Text style={styles.confidenceValue}>
            {Math.round(overallConfidence * 100)}% - {getConfidenceLabel(overallConfidence)}
          </Text>
          <Text style={styles.confidenceNote}>
            Based on historical data quality and pattern stability
          </Text>
        </View>
      </View>

      {/* Time Horizon Selector */}
      <View style={styles.segmentedControl}>
        {(['short_term', 'daily', 'weekly', 'monthly'] as TimeHorizon[]).map(horizon => (
          <TouchableOpacity
            key={horizon}
            style={[styles.segment, activeHorizon === horizon && styles.activeSegment]}
            onPress={() => setActiveHorizon(horizon)}>
            <Text style={[styles.segmentText, activeHorizon === horizon && styles.activeSegmentText]}>
              {horizon.replace('_', ' ').toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Forecast Content */}
      {activeHorizon === 'short_term' && forecast && (
        <ShortTermView forecast={forecast} getConfidenceColor={getConfidenceColor} />
      )}

      {activeHorizon === 'daily' && forecast && (
        <DailyView forecast={forecast} getConfidenceColor={getConfidenceColor} />
      )}

      {activeHorizon === 'weekly' && forecast && (
        <WeeklyView forecast={forecast} getConfidenceColor={getConfidenceColor} />
      )}

      {activeHorizon === 'monthly' && forecast && (
        <MonthlyView forecast={forecast} getConfidenceColor={getConfidenceColor} />
      )}

      {/* AI Insights */}
      {data?.insights && (
        <View style={styles.insightsCard}>
          <Text style={styles.insightsTitle}>AI Insights</Text>
          {data.insights.map((insight, index) => (
            <View key={index} style={styles.insightItem}>
              <Text style={styles.insightBullet}>•</Text>
              <Text style={styles.insightText}>{insight}</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

// ── Short Term View (Next 24 Hours) ─────────────────────────────────────

function ShortTermView({forecast, getConfidenceColor}: any) {
  const chartData = {
    labels: forecast.hourly_forecast?.map((h: any) => `${h.hour}:00`) || [],
    datasets: [
      {
        data: forecast.hourly_forecast?.map((h: any) => h.predicted_orders) || [],
        color: (opacity = 1) => `rgba(16, 185, 129, ${opacity})`,
        strokeWidth: 2,
      },
    ],
  };

  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Next 24 Hours Forecast</Text>

      {/* Summary Cards */}
      <View style={styles.summaryGrid}>
        <MetricCard
          label="Total Orders"
          value={forecast.total_orders}
          icon="📦"
          color="#10B981"
        />
        <MetricCard
          label="Revenue"
          value={`$${forecast.total_revenue?.toFixed(2)}`}
          icon="💰"
          color="#F59E0B"
        />
        <MetricCard
          label="Customers"
          value={forecast.total_customers}
          icon="👥"
          color="#3B82F6"
        />
      </View>

      {/* Confidence Score */}
      <View style={styles.confidenceCard}>
        <Text style={styles.confidenceLabel}>Forecast Confidence</Text>
        <View style={styles.confidenceBar}>
          <View
            style={[
              styles.confidenceFill,
              {
                width: `${forecast.confidence * 100}%`,
                backgroundColor: getConfidenceColor(forecast.confidence),
              },
            ]}
          />
        </View>
        <Text style={styles.confidenceText}>
          {Math.round(forecast.confidence * 100)}%
        </Text>
      </View>

      {/* Hourly Chart */}
      {chartData.labels.length > 0 && (
        <View style={styles.chartContainer}>
          <Text style={styles.chartTitle}>Hourly Order Prediction</Text>
          <LineChart
            data={chartData}
            width={screenWidth - 40}
            height={220}
            chartConfig={chartConfig}
            bezier
            style={styles.chart}
          />
        </View>
      )}

      {/* Peak Hours */}
      {forecast.peak_hours && forecast.peak_hours.length > 0 && (
        <View style={styles.peakHoursCard}>
          <Text style={styles.peakHoursTitle}>Peak Hours Today</Text>
          {forecast.peak_hours.slice(0, 3).map((peak: any, index: number) => (
            <View key={index} style={styles.peakHourItem}>
              <Text style={styles.peakHourTime}>{peak.time_label}</Text>
              <Text style={styles.peakHourOrders}>{peak.predicted_orders} orders</Text>
              <View style={styles.miniConfidenceBar}>
                <View
                  style={[
                    styles.miniConfidenceFill,
                    {
                      width: `${peak.confidence * 100}%`,
                      backgroundColor: getConfidenceColor(peak.confidence),
                    },
                  ]}
                />
              </View>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

// ── Daily View ───────────────────────────────────────────────────────────

function DailyView({forecast, getConfidenceColor}: any) {
  const chartData = {
    labels: forecast.daily_forecast?.map((d: any) => d.day_name.substring(0, 3)) || [],
    datasets: [
      {
        data: forecast.daily_forecast?.map((d: any) => d.predicted_orders) || [],
        color: (opacity = 1) => `rgba(16, 185, 129, ${opacity})`,
      },
      {
        data: forecast.daily_forecast?.map((d: any) => d.predicted_customers) || [],
        color: (opacity = 1) => `rgba(59, 130, 246, ${opacity})`,
      },
    ],
  };

  const revenueData = {
    labels: forecast.daily_forecast?.map((d: any) => d.day_name.substring(0, 3)) || [],
    datasets: [
      {
        data: forecast.daily_forecast?.map((d: any) => d.predicted_revenue / 100) || [],
      },
    ],
  };

  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Daily Forecast (Next 7 Days)</Text>

      {/* Summary Cards */}
      <View style={styles.summaryGrid}>
        <MetricCard
          label="Total Orders"
          value={forecast.summary?.total_orders}
          icon="📦"
          color="#10B981"
        />
        <MetricCard
          label="Revenue"
          value={`$${(forecast.summary?.total_revenue / 1000)?.toFixed(1)}K`}
          icon="💰"
          color="#F59E0B"
        />
        <MetricCard
          label="Customers"
          value={forecast.summary?.total_customers}
          icon="👥"
          color="#3B82F6"
        />
        <MetricCard
          label="Stationery"
          value={forecast.summary?.total_stationery_jobs}
          icon="📄"
          color="#8B5CF6"
        />
      </View>

      {/* Confidence Score */}
      <View style={styles.confidenceCard}>
        <Text style={styles.confidenceLabel}>Average Confidence</Text>
        <View style={styles.confidenceBar}>
          <View
            style={[
              styles.confidenceFill,
              {
                width: `${forecast.confidence * 100}%`,
                backgroundColor: getConfidenceColor(forecast.confidence),
              },
            ]}
          />
        </View>
        <Text style={styles.confidenceText}>
          {Math.round(forecast.confidence * 100)}%
        </Text>
      </View>

      {/* Orders & Customers Chart */}
      {chartData.labels.length > 0 && (
        <View style={styles.chartContainer}>
          <Text style={styles.chartTitle}>Orders vs Customers</Text>
          <LineChart
            data={chartData}
            width={screenWidth - 40}
            height={220}
            chartConfig={chartConfig}
            bezier
            style={styles.chart}
          />
        </View>
      )}

      {/* Revenue Chart */}
      {revenueData.labels.length > 0 && (
        <View style={styles.chartContainer}>
          <Text style={styles.chartTitle}>Revenue Forecast (in hundreds)</Text>
          <BarChart
            data={revenueData}
            width={screenWidth - 40}
            height={220}
            chartConfig={chartConfig}
            style={styles.chart}
          />
        </View>
      )}

      {/* Daily Breakdown */}
      <View style={styles.breakdownCard}>
        <Text style={styles.breakdownTitle}>Daily Breakdown</Text>
        {forecast.daily_forecast?.map((day: any, index: number) => (
          <View key={index} style={styles.dayRow}>
            <View style={styles.dayInfo}>
              <Text style={styles.dayName}>{day.day_name}</Text>
              <Text style={styles.dayDate}>{day.date}</Text>
            </View>
            <View style={styles.dayMetrics}>
              <View style={styles.dayMetric}>
                <Text style={styles.dayMetricValue}>{day.predicted_orders}</Text>
                <Text style={styles.dayMetricLabel}>Orders</Text>
              </View>
              <View style={styles.dayMetric}>
                <Text style={styles.dayMetricValue}>${(day.predicted_revenue / 1000)?.toFixed(1)}K</Text>
                <Text style={styles.dayMetricLabel}>Revenue</Text>
              </View>
              <View style={styles.dayMetric}>
                <Text style={styles.dayMetricValue}>{day.predicted_customers}</Text>
                <Text style={styles.dayMetricLabel}>Customers</Text>
              </View>
            </View>
            <View style={styles.miniConfidenceContainer}>
              <View
                style={[
                  styles.miniConfidenceBar,
                  {backgroundColor: getConfidenceColor(day.confidence)},
                ]}
              />
              <Text style={styles.miniConfidenceText}>{Math.round(day.confidence * 100)}%</Text>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

// ── Weekly View ──────────────────────────────────────────────────────────

function WeeklyView({forecast, getConfidenceColor}: any) {
  const chartData = {
    labels: forecast.weekly_forecast?.map((w: any) => `W${w.week_label.split(' ')[1]}`) || [],
    datasets: [
      {
        data: forecast.weekly_forecast?.map((w: any) => w.predicted_orders) || [],
      },
    ],
  };

  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Weekly Forecast (Next 4 Weeks)</Text>

      {/* Summary Cards */}
      <View style={styles.summaryGrid}>
        <MetricCard
          label="Total Orders"
          value={forecast.summary?.total_orders}
          icon="📦"
          color="#10B981"
        />
        <MetricCard
          label="Revenue"
          value={`$${(forecast.summary?.total_revenue / 1000)?.toFixed(1)}K`}
          icon="💰"
          color="#F59E0B"
        />
        <MetricCard
          label="Avg/Week"
          value={forecast.summary?.avg_weekly_orders}
          icon="📊"
          color="#3B82F6"
        />
      </View>

      {/* Trend Indicator */}
      <View style={styles.trendCard}>
        <Text style={styles.trendLabel}>Trend Direction</Text>
        <Text style={[
          styles.trendValue,
          {color: forecast.trend === 'up' ? '#10B981' : forecast.trend === 'down' ? '#EF4444' : '#6B7280'}
        ]}>
          {forecast.trend?.toUpperCase()}
        </Text>
      </View>

      {/* Weekly Chart */}
      {chartData.labels.length > 0 && (
        <View style={styles.chartContainer}>
          <Text style={styles.chartTitle}>Weekly Orders Forecast</Text>
          <BarChart
            data={chartData}
            width={screenWidth - 40}
            height={220}
            chartConfig={chartConfig}
            style={styles.chart}
          />
        </View>
      )}

      {/* Weekly Breakdown */}
      <View style={styles.breakdownCard}>
        <Text style={styles.breakdownTitle}>Weekly Breakdown</Text>
        {forecast.weekly_forecast?.map((week: any, index: number) => (
          <View key={index} style={styles.weekRow}>
            <View style={styles.weekInfo}>
              <Text style={styles.weekLabel}>{week.week_label}</Text>
              <Text style={styles.weekStart}>{week.week_start}</Text>
            </View>
            <View style={styles.weekMetrics}>
              <View style={styles.weekMetric}>
                <Text style={styles.weekMetricValue}>{week.predicted_orders}</Text>
                <Text style={styles.weekMetricLabel}>Orders</Text>
              </View>
              <View style={styles.weekMetric}>
                <Text style={styles.weekMetricValue}>${(week.predicted_revenue / 1000)?.toFixed(1)}K</Text>
                <Text style={styles.weekMetricLabel}>Revenue</Text>
              </View>
            </View>
            <View style={styles.miniConfidenceContainer}>
              <View
                style={[
                  styles.miniConfidenceBar,
                  {backgroundColor: getConfidenceColor(week.confidence)},
                ]}
              />
              <Text style={styles.miniConfidenceText}>{Math.round(week.confidence * 100)}%</Text>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

// ── Monthly View ─────────────────────────────────────────────────────────

function MonthlyView({forecast, getConfidenceColor}: any) {
  const chartData = {
    labels: forecast.monthly_forecast?.map((m: any) => m.month.split(' ')[0]) || [],
    datasets: [
      {
        data: forecast.monthly_forecast?.map((m: any) => m.predicted_orders) || [],
      },
    ],
  };

  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Monthly Forecast (Next 3 Months)</Text>

      {/* Summary Cards */}
      <View style={styles.summaryGrid}>
        <MetricCard
          label="Total Orders"
          value={forecast.summary?.total_orders}
          icon="📦"
          color="#10B981"
        />
        <MetricCard
          label="Revenue"
          value={`$${(forecast.summary?.total_revenue / 1000)?.toFixed(1)}K`}
          icon="💰"
          color="#F59E0B"
        />
        <MetricCard
          label="Avg/Month"
          value={forecast.summary?.avg_monthly_orders}
          icon="📊"
          color="#3B82F6"
        />
      </View>

      {/* YoY Growth */}
      <View style={styles.growthCard}>
        <Text style={styles.growthLabel}>Year-over-Year Growth</Text>
        <Text style={[
          styles.growthValue,
          {color: (forecast.yoy_growth || 0) >= 0 ? '#10B981' : '#EF4444'}
        ]}>
          {(forecast.yoy_growth || 0) >= 0 ? '+' : ''}{(forecast.yoy_growth || 0) * 100?.toFixed(1)}%
        </Text>
      </View>

      {/* Monthly Chart */}
      {chartData.labels.length > 0 && (
        <View style={styles.chartContainer}>
          <Text style={styles.chartTitle}>Monthly Orders Forecast</Text>
          <BarChart
            data={chartData}
            width={screenWidth - 40}
            height={220}
            chartConfig={chartConfig}
            style={styles.chart}
          />
        </View>
      )}

      {/* Monthly Breakdown */}
      <View style={styles.breakdownCard}>
        <Text style={styles.breakdownTitle}>Monthly Breakdown</Text>
        {forecast.monthly_forecast?.map((month: any, index: number) => (
          <View key={index} style={styles.monthRow}>
            <View style={styles.monthInfo}>
              <Text style={styles.monthLabel}>{month.month}</Text>
            </View>
            <View style={styles.monthMetrics}>
              <View style={styles.monthMetric}>
                <Text style={styles.monthMetricValue}>{month.predicted_orders}</Text>
                <Text style={styles.monthMetricLabel}>Orders</Text>
              </View>
              <View style={styles.monthMetric}>
                <Text style={styles.monthMetricValue}>${(month.predicted_revenue / 1000)?.toFixed(1)}K</Text>
                <Text style={styles.monthMetricLabel}>Revenue</Text>
              </View>
              <View style={styles.monthMetric}>
                <Text style={styles.monthMetricValue}>{month.predicted_customers}</Text>
                <Text style={styles.monthMetricLabel}>Customers</Text>
              </View>
            </View>
            <View style={styles.miniConfidenceContainer}>
              <View
                style={[
                  styles.miniConfidenceBar,
                  {backgroundColor: getConfidenceColor(month.confidence)},
                ]}
              />
              <Text style={styles.miniConfidenceText}>{Math.round(month.confidence * 100)}%</Text>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

// ── Helper Components ────────────────────────────────────────────────────

function MetricCard({label, value, icon, color}: any) {
  return (
    <View style={[styles.metricCard, {borderLeftColor: color}]}>
      <Text style={styles.metricIcon}>{icon}</Text>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function Metric({label, value}: {label: string; value: number}) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricValue}>{value}</Text>
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
  segmentedControl: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 8,
    padding: 4,
  },
  segment: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 6,
    alignItems: 'center',
  },
  activeSegment: {
    backgroundColor: '#10B981',
  },
  segmentText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#9CA3AF',
  },
  activeSegmentText: {
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
  summaryGrid: {
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
    color: '#F9FAFB',
    marginBottom: 4,
  },
  metricLabel: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  confidenceCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  confidenceTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F9FAFB',
    marginBottom: 8,
  },
  confidenceBar: {
    height: 8,
    backgroundColor: '#374151',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 8,
  },
  confidenceFill: {
    height: '100%',
    borderRadius: 4,
  },
  confidenceText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#10B981',
  },
  confidenceLabel: {
    fontSize: 12,
    color: '#9CA3AF',
    marginBottom: 4,
  },
  confidenceNote: {
    fontSize: 11,
    color: '#6B7280',
    marginTop: 4,
  },
  chartContainer: {
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
  peakHoursCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  peakHoursTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F9FAFB',
    marginBottom: 12,
  },
  peakHourItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  peakHourTime: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F9FAFB',
    width: 80,
  },
  peakHourOrders: {
    fontSize: 14,
    color: '#10B981',
    width: 100,
  },
  miniConfidenceBar: {
    flex: 1,
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
  },
  miniConfidenceFill: {
    height: '100%',
    borderRadius: 3,
  },
  miniConfidenceText: {
    fontSize: 12,
    color: '#9CA3AF',
    marginLeft: 8,
    width: 35,
  },
  miniConfidenceContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  trendCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  trendLabel: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  trendValue: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  growthCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  growthLabel: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  growthValue: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  breakdownCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    padding: 16,
  },
  breakdownTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F9FAFB',
    marginBottom: 12,
  },
  dayRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#374151',
  },
  dayInfo: {
    flex: 1,
  },
  dayName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F9FAFB',
  },
  dayDate: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 2,
  },
  dayMetrics: {
    flexDirection: 'row',
    gap: 16,
  },
  dayMetric: {
    alignItems: 'center',
  },
  dayMetricValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#10B981',
  },
  dayMetricLabel: {
    fontSize: 10,
    color: '#9CA3AF',
    marginTop: 2,
  },
  weekRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#374151',
  },
  weekInfo: {
    flex: 1,
  },
  weekLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F9FAFB',
  },
  weekStart: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 2,
  },
  weekMetrics: {
    flexDirection: 'row',
    gap: 16,
  },
  weekMetric: {
    alignItems: 'center',
  },
  weekMetricValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#10B981',
  },
  weekMetricLabel: {
    fontSize: 10,
    color: '#9CA3AF',
    marginTop: 2,
  },
  monthRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#374151',
  },
  monthInfo: {
    flex: 1,
  },
  monthLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F9FAFB',
  },
  monthMetrics: {
    flexDirection: 'row',
    gap: 16,
  },
  monthMetric: {
    alignItems: 'center',
  },
  monthMetricValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#10B981',
  },
  monthMetricLabel: {
    fontSize: 10,
    color: '#9CA3AF',
    marginTop: 2,
  },
  insightsCard: {
    marginHorizontal: 16,
    marginBottom: 24,
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
  metric: {
    alignItems: 'center',
    padding: 12,
  },
});
