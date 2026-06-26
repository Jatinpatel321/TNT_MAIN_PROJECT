import React, { useEffect, useState } from 'react';
import { Alert, Image, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { Text } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { toAbsoluteUrl } from '../../utils/url';
import { formatMoneyPaise } from '../../utils/format';
import {
  getSuggestedReorder,
  getPredictionInsights,
  getPredictionAccuracy,
} from '../../services/recommendationService';
import type {
  SuggestedReorderResponse,
  PredictionInsightsResponse,
} from '../../services/recommendationService';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function PredictionsScreen() {
  const navigation = useNavigation<Nav>();
  const [suggestedReorder, setSuggestedReorder] = useState<SuggestedReorderResponse | null>(null);
  const [insights, setInsights] = useState<PredictionInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPredictions();
  }, []);

  const loadPredictions = async () => {
    try {
      setLoading(true);
      const [reorder, insightsData] = await Promise.all([
        getSuggestedReorder().catch(() => null),
        getPredictionInsights().catch(() => null),
      ]);

      if (reorder) setSuggestedReorder(reorder);
      if (insightsData) setInsights(insightsData);
    } catch (e) {
      Alert.alert('Error', 'Failed to load predictions');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return '#059669'; // Green
    if (confidence >= 0.6) return '#D97706'; // Orange
    return '#DC2626'; // Red
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
  };

  const getDayName = (day: number) => {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return days[day] || 'Unknown';
  };

  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  if (loading) {
    return (
      <Screen>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Analyzing your ordering patterns...</Text>
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <MaterialCommunityIcons name="brain" size={28} color="#7C3AED" />
          <View style={styles.headerText}>
            <Text style={styles.headerTitle}>Smart Predictions</Text>
            <Text style={styles.headerSubtitle}>AI-powered ordering insights</Text>
          </View>
        </View>

        {/* Suggested Reorder Section */}
        {suggestedReorder && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="cart-check" size={22} color="#2563EB" />
              <Text style={styles.sectionTitle}>Suggested Reorder</Text>
            </View>

            {/* Confidence Badge */}
            <View style={styles.confidenceContainer}>
              <View style={[
                styles.confidenceBadge,
                { backgroundColor: getConfidenceColor(suggestedReorder.confidence) + '20' }
              ]}>
                <MaterialCommunityIcons
                  name="check-decagram"
                  size={20}
                  color={getConfidenceColor(suggestedReorder.confidence)}
                />
                <Text style={[
                  styles.confidenceText,
                  { color: getConfidenceColor(suggestedReorder.confidence) }
                ]}>
                  {getConfidenceLabel(suggestedReorder.confidence)} Confidence
                </Text>
                <Text style={[
                  styles.confidenceValue,
                  { color: getConfidenceColor(suggestedReorder.confidence) }
                ]}>
                  {Math.round(suggestedReorder.confidence * 100)}%
                </Text>
              </View>
            </View>

            {/* Suggested Items */}
            <View style={styles.itemsContainer}>
              {suggestedReorder.suggested_items.map((item) => {
                const remoteUri = toAbsoluteUrl(item.image_url);
                const source = remoteUri ? { uri: remoteUri } : null;
                return (
                  <TouchableOpacity
                    key={item.item_id}
                    style={styles.itemCard}
                    onPress={() => navigation.navigate('Menu', { vendorId: item.vendor_id })}
                  >
                    {source ? (
                      <Image source={source} style={styles.itemImage} />
                    ) : (
                      <View style={styles.itemImagePlaceholder}>
                        <MaterialCommunityIcons name="food" size={24} color="#D1D5DB" />
                      </View>
                    )}
                    <View style={styles.itemInfo}>
                      <Text style={styles.itemName} numberOfLines={1}>{item.item_name}</Text>
                      <Text style={styles.itemPrice}>{formatMoneyPaise(item.price)}</Text>
                      <Text style={styles.itemReason} numberOfLines={1}>{item.reason}</Text>
                    </View>
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* Suggested Time */}
            <View style={styles.timeCard}>
              <MaterialCommunityIcons name="clock-outline" size={20} color="#0891B2" />
              <View style={styles.timeInfo}>
                <Text style={styles.timeLabel}>Recommended Time</Text>
                <Text style={styles.timeValue}>{formatTime(suggestedReorder.suggested_time)}</Text>
                <Text style={styles.timeReason}>
                  Based on your {suggestedReorder.patterns.daily.daily_pattern} pattern
                </Text>
              </View>
            </View>

            {/* Reasoning */}
            <View style={styles.reasoningCard}>
              <MaterialCommunityIcons name="lightbulb-outline" size={20} color="#D97706" />
              <View style={styles.reasoningInfo}>
                <Text style={styles.reasoningLabel}>Why this suggestion?</Text>
                <Text style={styles.reasoningText}>{suggestedReorder.reasoning}</Text>
              </View>
            </View>
          </View>
        )}

        {/* Weekly Patterns */}
        {insights && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="calendar-week" size={22} color="#7C3AED" />
              <Text style={styles.sectionTitle}>Weekly Patterns</Text>
            </View>

            <View style={styles.patternCard}>
              <View style={styles.patternRow}>
                <Text style={styles.patternLabel}>Pattern:</Text>
                <Text style={styles.patternValue}>
                  {insights.weekly_patterns.weekly_pattern.replace(/_/g, ' ').toUpperCase()}
                </Text>
              </View>

              {insights.weekly_patterns.preferred_days.length > 0 && (
                <View style={styles.patternRow}>
                  <Text style={styles.patternLabel}>Preferred Days:</Text>
                  <View style={styles.daysContainer}>
                    {insights.weekly_patterns.preferred_days.map((day) => (
                      <View key={day} style={styles.dayBadge}>
                        <Text style={styles.dayText}>{getDayName(day).slice(0, 3)}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              )}
            </View>
          </View>
        )}

        {/* Daily Patterns */}
        {insights && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="clock-time-four" size={22} color="#0891B2" />
              <Text style={styles.sectionTitle}>Daily Patterns</Text>
            </View>

            <View style={styles.patternCard}>
              <View style={styles.patternRow}>
                <Text style={styles.patternLabel}>Pattern:</Text>
                <Text style={styles.patternValue}>
                  {insights.daily_patterns.daily_pattern.replace(/_/g, ' ').toUpperCase()}
                </Text>
              </View>

              <View style={styles.patternRow}>
                <Text style={styles.patternLabel}>Preferred Hour:</Text>
                <Text style={styles.patternValue}>
                  {insights.daily_patterns.preferred_hour}:00
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* Favourite Vendors */}
        {insights && insights.favourite_vendors.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="store" size={22} color="#059669" />
              <Text style={styles.sectionTitle}>Favourite Vendors</Text>
            </View>

            {insights.favourite_vendors.slice(0, 5).map((vendor) => (
              <TouchableOpacity
                key={vendor.vendor_id}
                style={styles.vendorCard}
                onPress={() => navigation.navigate('Menu', { vendorId: vendor.vendor_id, vendorName: vendor.vendor_name })}
              >
                <View style={styles.vendorInfo}>
                  <Text style={styles.vendorName}>{vendor.vendor_name}</Text>
                  <Text style={styles.vendorMeta}>
                    {vendor.order_count} orders · {vendor.vendor_type}
                  </Text>
                </View>
                <View style={[
                  styles.confidenceSmall,
                  { backgroundColor: getConfidenceColor(vendor.confidence) + '20' }
                ]}>
                  <Text style={[
                    styles.confidenceSmallText,
                    { color: getConfidenceColor(vendor.confidence) }
                  ]}>
                    {Math.round(vendor.confidence * 100)}%
                  </Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* Favourite Foods */}
        {insights && insights.favourite_foods.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="food" size={22} color="#D97706" />
              <Text style={styles.sectionTitle}>Favourite Foods</Text>
            </View>

            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {insights.favourite_foods.slice(0, 8).map((food) => (
                <View key={food.item_id} style={styles.foodCard}>
                  <Text style={styles.foodName} numberOfLines={1}>{food.name}</Text>
                  <Text style={styles.foodMeta}>
                    {food.order_count} orders
                  </Text>
                  <View style={[
                    styles.confidenceSmall,
                    { backgroundColor: getConfidenceColor(food.confidence) + '20' }
                  ]}>
                    <Text style={[
                      styles.confidenceSmallText,
                      { color: getConfidenceColor(food.confidence) }
                    ]}>
                      {Math.round(food.confidence * 100)}%
                    </Text>
                  </View>
                </View>
              ))}
            </ScrollView>
          </View>
        )}

        {/* Favourite Stationery */}
        {insights && insights.favourite_stationery.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="file-document" size={22} color="#2563EB" />
              <Text style={styles.sectionTitle}>Favourite Stationery</Text>
            </View>

            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {insights.favourite_stationery.slice(0, 6).map((item) => (
                <View key={item.item_id} style={styles.foodCard}>
                  <Text style={styles.foodName} numberOfLines={1}>{item.name}</Text>
                  <Text style={styles.foodMeta}>
                    {item.order_count} orders
                  </Text>
                  <View style={[
                    styles.confidenceSmall,
                    { backgroundColor: getConfidenceColor(item.confidence) + '20' }
                  ]}>
                    <Text style={[
                      styles.confidenceSmallText,
                      { color: getConfidenceColor(item.confidence) }
                    ]}>
                      {Math.round(item.confidence * 100)}%
                    </Text>
                  </View>
                </View>
              ))}
            </ScrollView>
          </View>
        )}

        {/* Prediction Accuracy */}
        {insights && insights.prediction_accuracy.total_predictions > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="chart-line" size={22} color="#DB2777" />
              <Text style={styles.sectionTitle}>Prediction Accuracy</Text>
            </View>

            <View style={styles.accuracyCard}>
              <View style={styles.accuracyMain}>
                <Text style={styles.accuracyValue}>
                  {insights.prediction_accuracy.accuracy}%
                </Text>
                <Text style={styles.accuracyLabel}>Overall Accuracy</Text>
                <Text style={styles.accuracySubtext}>
                  {insights.prediction_accuracy.correct_predictions} of {insights.prediction_accuracy.total_predictions} predictions correct
                </Text>
              </View>

              {Object.entries(insights.prediction_accuracy.by_type).map(([type, stats]) => (
                <View key={type} style={styles.accuracyRow}>
                  <Text style={styles.accuracyType}>{type.replace(/_/g, ' ')}</Text>
                  <View style={styles.accuracyBar}>
                    <View
                      style={[
                        styles.accuracyFill,
                        {
                          width: `${stats.accuracy}%`,
                          backgroundColor: getConfidenceColor(stats.accuracy / 100),
                        }
                      ]}
                    />
                  </View>
                  <Text style={styles.accuracyPercent}>{stats.accuracy}%</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Refresh Button */}
        <TouchableOpacity style={styles.refreshButton} onPress={loadPredictions}>
          <MaterialCommunityIcons name="refresh" size={20} color="#FFFFFF" />
          <Text style={styles.refreshButtonText}>Refresh Predictions</Text>
        </TouchableOpacity>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  loadingText: {
    fontSize: 16,
    color: '#6B7280',
    marginTop: 12,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 20,
  },
  headerText: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '800',
    color: '#111827',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 2,
  },
  section: {
    marginBottom: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
  },
  confidenceContainer: {
    marginBottom: 12,
  },
  confidenceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 12,
    borderRadius: 12,
  },
  confidenceText: {
    fontSize: 14,
    fontWeight: '600',
    flex: 1,
  },
  confidenceValue: {
    fontSize: 18,
    fontWeight: '800',
  },
  itemsContainer: {
    gap: 10,
    marginBottom: 12,
  },
  itemCard: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    gap: 12,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 3,
    elevation: 2,
  },
  itemImage: {
    width: 60,
    height: 60,
    borderRadius: 8,
    backgroundColor: '#F3F4F6',
  },
  itemImagePlaceholder: {
    width: 60,
    height: 60,
    borderRadius: 8,
    backgroundColor: '#F3F4F6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemInfo: {
    flex: 1,
    justifyContent: 'center',
  },
  itemName: {
    fontSize: 15,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 4,
  },
  itemPrice: {
    fontSize: 14,
    fontWeight: '600',
    color: '#7C3AED',
    marginBottom: 2,
  },
  itemReason: {
    fontSize: 12,
    color: '#6B7280',
  },
  timeCard: {
    flexDirection: 'row',
    backgroundColor: '#F0FDFA',
    borderRadius: 12,
    padding: 14,
    gap: 12,
    marginBottom: 10,
  },
  timeInfo: {
    flex: 1,
  },
  timeLabel: {
    fontSize: 12,
    color: '#0891B2',
    fontWeight: '600',
    marginBottom: 4,
  },
  timeValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 2,
  },
  timeReason: {
    fontSize: 12,
    color: '#6B7280',
  },
  reasoningCard: {
    flexDirection: 'row',
    backgroundColor: '#FFFBEB',
    borderRadius: 12,
    padding: 14,
    gap: 12,
    borderWidth: 1,
    borderColor: '#FEF3C7',
  },
  reasoningInfo: {
    flex: 1,
  },
  reasoningLabel: {
    fontSize: 12,
    color: '#D97706',
    fontWeight: '600',
    marginBottom: 4,
  },
  reasoningText: {
    fontSize: 13,
    color: '#374151',
    lineHeight: 18,
  },
  patternCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 14,
    gap: 10,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 3,
    elevation: 2,
  },
  patternRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  patternLabel: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  patternValue: {
    fontSize: 14,
    color: '#111827',
    fontWeight: '700',
    textTransform: 'capitalize',
  },
  daysContainer: {
    flexDirection: 'row',
    gap: 6,
  },
  dayBadge: {
    backgroundColor: '#7C3AED20',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  dayText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#7C3AED',
  },
  vendorCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    gap: 10,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 3,
    elevation: 2,
  },
  vendorInfo: {
    flex: 1,
  },
  vendorName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 2,
  },
  vendorMeta: {
    fontSize: 12,
    color: '#6B7280',
  },
  confidenceSmall: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  confidenceSmallText: {
    fontSize: 12,
    fontWeight: '700',
  },
  foodCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    padding: 10,
    marginRight: 10,
    minWidth: 120,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 3,
    elevation: 2,
  },
  foodName: {
    fontSize: 13,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 4,
  },
  foodMeta: {
    fontSize: 11,
    color: '#6B7280',
    marginBottom: 6,
  },
  accuracyCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    gap: 12,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 3,
    elevation: 2,
  },
  accuracyMain: {
    alignItems: 'center',
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  accuracyValue: {
    fontSize: 36,
    fontWeight: '800',
    color: '#7C3AED',
  },
  accuracyLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginTop: 4,
  },
  accuracySubtext: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  accuracyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  accuracyType: {
    fontSize: 12,
    color: '#6B7280',
    width: 100,
    textTransform: 'capitalize',
  },
  accuracyBar: {
    flex: 1,
    height: 8,
    backgroundColor: '#F3F4F6',
    borderRadius: 4,
    overflow: 'hidden',
  },
  accuracyFill: {
    height: '100%',
    borderRadius: 4,
  },
  accuracyPercent: {
    fontSize: 12,
    fontWeight: '700',
    color: '#374151',
    width: 40,
    textAlign: 'right',
  },
  refreshButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#7C3AED',
    padding: 14,
    borderRadius: 12,
    marginTop: 10,
  },
  refreshButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
});
</write_to_file>
<task_progress>
- [x] Add prediction history model to database
- [x] Create prediction service with ML algorithms
- [x] Implement weekly/daily/semester pattern learning
- [x] Create prediction API endpoints
- [x] Build frontend prediction screen
- [x] Add migration for prediction tables
- [ ] Integrate with existing recommendation engine
- [ ] Test prediction accuracy
</task_progress>
</write_to_file>