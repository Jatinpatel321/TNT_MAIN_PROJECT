import React, { useEffect, useState } from 'react';
import { Alert, Image, ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { Text } from 'react-native-paper';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp, NativeStackScreenProps } from '@react-navigation/native-stack';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { toAbsoluteUrl } from '../../utils/url';
import { getEnhancedETA, getETAFactors } from '../../services/enhancedETAService';
import type { EnhancedETAResponse, ETAFactorsResponse } from '../../services/enhancedETAService';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Props = NativeStackScreenProps<RootStackParamList, 'OrderTracking'>;

export function OrderTrackingScreen({ route }: Props) {
  const navigation = useNavigation<Nav>();
  const { orderId } = route.params;
  const [etaData, setEtaData] = useState<EnhancedETAResponse | null>(null);
  const [factors, setFactors] = useState<ETAFactorsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadETAData();
  }, [orderId]);

  const loadETAData = async () => {
    try {
      setLoading(true);
      const [eta, factorsData] = await Promise.all([
        getEnhancedETA(orderId).catch(() => null),
        getETAFactors(orderId).catch(() => null),
      ]);
      if (eta) setEtaData(eta);
      if (factorsData) setFactors(factorsData);
    } catch (e) {
      Alert.alert('Error', 'Failed to load ETA data');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadETAData();
    setRefreshing(false);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return '#059669';
    if (confidence >= 0.6) return '#D97706';
    return '#DC2626';
  };

  const getDelayRiskColor = (risk: string) => {
    switch (risk) {
      case 'HIGH': return '#DC2626';
      case 'MEDIUM': return '#D97706';
      case 'LOW': return '#059669';
      default: return '#6B7280';
    }
  };

  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  if (loading) {
    return (
      <Screen>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Calculating ETA...</Text>
        </View>
      </Screen>
    );
  }

  if (!etaData) {
    return (
      <Screen>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Unable to load ETA</Text>
          <TouchableOpacity style={styles.retryButton} onPress={loadETAData}>
            <Text style={styles.retryButtonText}>Retry</Text>
          </TouchableOpacity>
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <MaterialCommunityIcons name="clock-fast" size={28} color="#2563EB" />
          <View style={styles.headerText}>
            <Text style={styles.headerTitle}>Order ETA</Text>
            <Text style={styles.headerSubtitle}>Order #{orderId}</Text>
          </View>
          <TouchableOpacity onPress={handleRefresh} disabled={refreshing}>
            <MaterialCommunityIcons 
              name="refresh" 
              size={24} 
              color={refreshing ? "#9CA3AF" : "#2563EB"} 
            />
          </TouchableOpacity>
        </View>

        {/* Main ETA Card */}
        <View style={styles.etaCard}>
          <View style={styles.etaMain}>
            <Text style={styles.etaValue}>{etaData.predicted_eta_minutes}</Text>
            <Text style={styles.etaLabel}>minutes</Text>
          </View>

          <View style={styles.etaDivider} />

          <View style={styles.etaInfo}>
            <View style={styles.etaRow}>
              <MaterialCommunityIcons name="clock-outline" size={18} color="#0891B2" />
              <Text style={styles.etaInfoLabel}>Ready at</Text>
              <Text style={styles.etaInfoValue}>{formatTime(etaData.estimated_ready_at)}</Text>
            </View>

            <View style={styles.etaRow}>
              <MaterialCommunityIcons 
                name="shield-check" 
                size={18} 
                color={getConfidenceColor(etaData.confidence)} 
              />
              <Text style={styles.etaInfoLabel}>Confidence</Text>
              <View style={[
                styles.confidenceBadge,
                { backgroundColor: getConfidenceColor(etaData.confidence) + '20' }
              ]}>
                <Text style={[
                  styles.confidenceText,
                  { color: getConfidenceColor(etaData.confidence) }
                ]}>
                  {Math.round(etaData.confidence * 100)}%
                </Text>
              </View>
            </View>

            <View style={styles.etaRow}>
              <MaterialCommunityIcons 
                name="alert-circle" 
                size={18} 
                color={getDelayRiskColor(etaData.delay_risk_level)} 
              />
              <Text style={styles.etaInfoLabel}>Delay Risk</Text>
              <View style={[
                styles.riskBadge,
                { backgroundColor: getDelayRiskColor(etaData.delay_risk_level) + '20' }
              ]}>
                <Text style={[
                  styles.riskText,
                  { color: getDelayRiskColor(etaData.delay_risk_level) }
                ]}>
                  {etaData.delay_risk_level}
                </Text>
              </View>
            </View>
          </View>
        </View>

        {/* Delay Prediction */}
        {etaData.delay_prediction && etaData.delay_prediction.delay_probability > 0.3 && (
          <View style={styles.delayCard}>
            <View style={styles.delayHeader}>
              <MaterialCommunityIcons name="alert" size={20} color="#D97706" />
              <Text style={styles.delayTitle}>Delay Warning</Text>
            </View>

            <View style={styles.delayContent}>
              <Text style={styles.delayProbability}>
                {Math.round(etaData.delay_prediction.delay_probability * 100)}% chance of delay
              </Text>
              {etaData.delay_prediction.expected_delay_minutes > 0 && (
                <Text style={styles.delayExpected}>
                  Expected delay: +{etaData.delay_prediction.expected_delay_minutes} minutes
                </Text>
              )}

              {etaData.delay_prediction.risk_factors.length > 0 && (
                <View style={styles.riskFactors}>
                  <Text style={styles.riskFactorsLabel}>Risk Factors:</Text>
                  {etaData.delay_prediction.risk_factors.map((factor, index) => (
                    <View key={index} style={styles.riskFactorItem}>
                      <MaterialCommunityIcons name="circle-small" size={16} color="#D97706" />
                      <Text style={styles.riskFactorText}>{factor}</Text>
                    </View>
                  ))}
                </View>
              )}

              {etaData.delay_prediction.recommendations.length > 0 && (
                <View style={styles.recommendations}>
                  <Text style={styles.recommendationsLabel}>Recommendations:</Text>
                  {etaData.delay_prediction.recommendations.map((rec, index) => (
                    <View key={index} style={styles.recommendationItem}>
                      <MaterialCommunityIcons name="lightbulb-outline" size={16} color="#0891B2" />
                      <Text style={styles.recommendationText}>{rec}</Text>
                    </View>
                  ))}
                </View>
              )}
            </View>
          </View>
        )}

        {/* Preparation Progress */}
        {etaData.preparation_progress && (
          <View style={styles.progressCard}>
            <View style={styles.progressHeader}>
              <MaterialCommunityIcons name="progress-check" size={20} color="#7C3AED" />
              <Text style={styles.progressTitle}>Preparation Progress</Text>
            </View>

            <View style={styles.progressTimeline}>
              <View style={styles.progressStep}>
                <View style={[styles.progressDot, styles.progressDotActive]} />
                <Text style={styles.progressLabel}>Order Placed</Text>
              </View>
              <View style={styles.progressLine} />
              <View style={styles.progressStep}>
                <View style={[styles.progressDot, styles.progressDotActive]} />
                <Text style={styles.progressLabel}>Preparing</Text>
              </View>
              <View style={styles.progressLine} />
              <View style={styles.progressStep}>
                <View style={styles.progressDot} />
                <Text style={styles.progressLabel}>Ready</Text>
              </View>
            </View>
          </View>
        )}

        {/* ETA Factors Breakdown */}
        {factors && (
          <View style={styles.factorsCard}>
            <View style={styles.factorsHeader}>
              <MaterialCommunityIcons name="chart-bar" size={20} color="#059669" />
              <Text style={styles.factorsTitle}>ETA Factors</Text>
            </View>

            <View style={styles.factorRow}>
              <Text style={styles.factorLabel}>Base ETA</Text>
              <Text style={styles.factorValue}>{etaData.factors.base_eta} min</Text>
            </View>

            <View style={styles.factorRow}>
              <Text style={styles.factorLabel}>Complexity Factor</Text>
              <View style={styles.factorBar}>
                <View 
                  style={[
                    styles.factorFill, 
                    { 
                      width: `${etaData.factors.avg_complexity * 100}%`,
                      backgroundColor: '#D97706'
                    }
                  ]} 
                />
              </View>
              <Text style={styles.factorPercent}>{Math.round(etaData.factors.avg_complexity * 100)}%</Text>
            </View>

            <View style={styles.factorRow}>
              <Text style={styles.factorLabel}>Workload Factor</Text>
              <View style={styles.factorBar}>
                <View 
                  style={[
                    styles.factorFill, 
                    { 
                      width: `${etaData.factors.vendor_workload.workload_score * 100}%`,
                      backgroundColor: '#DC2626'
                    }
                  ]} 
                />
              </View>
              <Text style={styles.factorPercent}>{Math.round(etaData.factors.vendor_workload.workload_score * 100)}%</Text>
            </View>

            <View style={styles.factorRow}>
              <Text style={styles.factorLabel}>Time Factor</Text>
              <View style={styles.factorBar}>
                <View 
                  style={[
                    styles.factorFill, 
                    { 
                      width: `${etaData.factors.slot_occupancy.utilization * 100}%`,
                      backgroundColor: '#2563EB'
                    }
                  ]} 
                />
              </View>
              <Text style={styles.factorPercent}>{Math.round(etaData.factors.slot_occupancy.utilization * 100)}%</Text>
            </View>

            {factors.vendor_workload && (
              <View style={styles.vendorInfo}>
                <Text style={styles.vendorInfoLabel}>Vendor Workload</Text>
                <Text style={styles.vendorInfoValue}>
                  {factors.vendor_workload.active_orders} active orders
                </Text>
                <Text style={styles.vendorInfoSubtext}>
                  {Math.round(factors.vendor_workload.completion_rate * 100)}% completion rate
                </Text>
              </View>
            )}
          </View>
        )}

        {/* Live Update Button */}
        <TouchableOpacity style={styles.updateButton} onPress={handleRefresh}>
          <MaterialCommunityIcons name="refresh" size={20} color="#FFFFFF" />
          <Text style={styles.updateButtonText}>Update ETA</Text>
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
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  errorText: {
    fontSize: 16,
    color: '#DC2626',
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: '#2563EB',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
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
  etaCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 20,
    gap: 16,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 8,
    elevation: 4,
    marginBottom: 16,
  },
  etaMain: {
    alignItems: 'center',
    paddingVertical: 10,
  },
  etaValue: {
    fontSize: 56,
    fontWeight: '800',
    color: '#2563EB',
  },
  etaLabel: {
    fontSize: 16,
    color: '#6B7280',
    marginTop: 4,
  },
  etaDivider: {
    height: 1,
    backgroundColor: '#E5E7EB',
  },
  etaInfo: {
    gap: 12,
  },
  etaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  etaInfoLabel: {
    fontSize: 14,
    color: '#6B7280',
    flex: 1,
  },
  etaInfoValue: {
    fontSize: 15,
    fontWeight: '700',
    color: '#111827',
  },
  confidenceBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  confidenceText: {
    fontSize: 13,
    fontWeight: '700',
  },
  riskBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  riskText: {
    fontSize: 13,
    fontWeight: '700',
  },
  delayCard: {
    backgroundColor: '#FEF3C7',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#FCD34D',
  },
  delayHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  delayTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#92400E',
  },
  delayContent: {
    gap: 8,
  },
  delayProbability: {
    fontSize: 18,
    fontWeight: '700',
    color: '#DC2626',
  },
  delayExpected: {
    fontSize: 14,
    color: '#374151',
  },
  riskFactors: {
    marginTop: 8,
  },
  riskFactorsLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#92400E',
    marginBottom: 4,
  },
  riskFactorItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginVertical: 2,
  },
  riskFactorText: {
    fontSize: 13,
    color: '#374151',
  },
  recommendations: {
    marginTop: 8,
  },
  recommendationsLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#0891B2',
    marginBottom: 4,
  },
  recommendationItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginVertical: 2,
  },
  recommendationText: {
    fontSize: 13,
    color: '#374151',
  },
  progressCard: {
    backgroundColor: '#F5F3FF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  progressHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  progressTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#6D28D9',
  },
  progressTimeline: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  progressStep: {
    alignItems: 'center',
    gap: 6,
  },
  progressDot: {
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: '#E5E7EB',
  },
  progressDotActive: {
    backgroundColor: '#7C3AED',
  },
  progressLine: {
    flex: 1,
    height: 2,
    backgroundColor: '#E5E7EB',
    marginHorizontal: 8,
  },
  progressLabel: {
    fontSize: 11,
    color: '#6B7280',
    fontWeight: '500',
  },
  factorsCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 3,
    elevation: 2,
  },
  factorsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  factorsTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#059669',
  },
  factorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  factorLabel: {
    fontSize: 13,
    color: '#6B7280',
    width: 120,
  },
  factorBar: {
    flex: 1,
    height: 8,
    backgroundColor: '#F3F4F6',
    borderRadius: 4,
    overflow: 'hidden',
  },
  factorFill: {
    height: '100%',
    borderRadius: 4,
  },
  factorPercent: {
    fontSize: 12,
    fontWeight: '700',
    color: '#374151',
    width: 40,
    textAlign: 'right',
  },
  vendorInfo: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  vendorInfoLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 4,
  },
  vendorInfoValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
  },
  vendorInfoSubtext: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  updateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#2563EB',
    padding: 14,
    borderRadius: 12,
    marginTop: 10,
  },
  updateButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
});
</write_to_file>
<task_progress>
- [x] Find existing ETA implementation
- [x] Analyze current ETA engine
- [x] Enhance ETA prediction with ML
- [x] Add historical preparation times
- [x] Add vendor workload analysis
- [x] Add slot occupancy tracking
- [x] Add menu complexity scoring
- [x] Implement delay prediction
- [x] Create preparation progress tracking
- [x] Extend existing ETA APIs
- [x] Build frontend ETA components
- [ ] Create documentation
</task_progress>
</write_to_file>