import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import {
  getBestPickupTime,
  getPeakHourAlerts,
} from '../../services/recommendationService';
import type {
  BestPickupTimeResponse,
  PeakHourAlertData,
  PickupTimeSlot,
} from '../../services/recommendationService';

type Props = NativeStackScreenProps<RootStackParamList, 'BestTime'>;

function CongestionBadge({ level }: { level: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    LOW: { bg: '#D1FAE5', text: '#059669', label: 'Low' },
    MEDIUM: { bg: '#FEF3C7', text: '#D97706', label: 'Medium' },
    HIGH: { bg: '#FEE2E2', text: '#DC2626', label: 'High' },
    CRITICAL: { bg: '#FEE2E2', text: '#991B1B', label: 'Critical' },
  };
  const c = config[level] ?? config.LOW;
  return (
    <View style={[styles.badge, { backgroundColor: c.bg }]}>
      <Text style={[styles.badgeText, { color: c.text }]}>{c.label}</Text>
    </View>
  );
}

function DelayBadge({ risk }: { risk: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    LOW: { bg: '#D1FAE5', text: '#059669', label: 'Low Risk' },
    MEDIUM: { bg: '#FEF3C7', text: '#D97706', label: 'Medium Risk' },
    HIGH: { bg: '#FEE2E2', text: '#DC2626', label: 'High Risk' },
  };
  const c = config[risk] ?? config.LOW;
  return (
    <View style={[styles.badge, { backgroundColor: c.bg }]}>
      <Text style={[styles.badgeText, { color: c.text }]}>{c.label}</Text>
    </View>
  );
}

export function BestTimeScreen({ navigation }: Props) {
  const [pickupData, setPickupData] = useState<BestPickupTimeResponse | null>(null);
  const [peakData, setPeakData] = useState<PeakHourAlertData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setError(null);
      const [pickup, peak] = await Promise.all([
        getBestPickupTime(),
        getPeakHourAlerts(),
      ]);
      setPickupData(pickup);
      setPeakData(peak);
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        'Unable to load pickup time data. Please check your connection and try again.';
      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  if (loading) {
    return (
      <Screen>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#3B82F6" />
          <Text style={styles.loadingText}>Loading best pickup times...</Text>
        </View>
      </Screen>
    );
  }

  if (error) {
    return (
      <Screen>
        <ScrollView
          contentContainerStyle={styles.scroll}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        >
          <View style={styles.header}>
            <Pressable onPress={() => navigation.goBack()} style={styles.backBtn}>
              <MaterialCommunityIcons name="arrow-left" size={22} color="#111827" />
            </Pressable>
            <Text style={styles.title}>Best Time to Order</Text>
          </View>
          <View style={styles.errorCard}>
            <MaterialCommunityIcons name="alert-circle-outline" size={40} color="#DC2626" />
            <Text style={styles.errorTitle}>Something went wrong</Text>
            <Text style={styles.errorMessage}>{error}</Text>
            <Pressable style={styles.retryButton} onPress={onRefresh}>
              <Text style={styles.retryButtonText}>Try Again</Text>
            </Pressable>
          </View>
        </ScrollView>
      </Screen>
    );
  }

  if (!pickupData && !peakData) {
    return (
      <Screen>
        <ScrollView
          contentContainerStyle={styles.scroll}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        >
          <View style={styles.header}>
            <Pressable onPress={() => navigation.goBack()} style={styles.backBtn}>
              <MaterialCommunityIcons name="arrow-left" size={22} color="#111827" />
            </Pressable>
            <Text style={styles.title}>Best Time to Order</Text>
          </View>
          <View style={styles.emptyCard}>
            <MaterialCommunityIcons name="clock-outline" size={40} color="#9CA3AF" />
            <Text style={styles.emptyTitle}>No data available</Text>
            <Text style={styles.emptyMessage}>
              We couldn't find any pickup time recommendations yet. Start ordering to get
              personalized suggestions.
            </Text>
          </View>
        </ScrollView>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Pressable onPress={() => navigation.goBack()} style={styles.backBtn}>
            <MaterialCommunityIcons name="arrow-left" size={22} color="#111827" />
          </Pressable>
          <Text style={styles.title}>Best Time to Order</Text>
        </View>

        {/* Peak Hour Alert Banner */}
        {peakData && (
          <View
            style={[
              styles.peakBanner,
              peakData.is_peak_now ? styles.peakBannerActive : styles.peakBannerClear,
            ]}
          >
            <View style={styles.peakBannerLeft}>
              <MaterialCommunityIcons
                name={peakData.is_peak_now ? 'alert-circle' : 'check-circle'}
                size={24}
                color={peakData.is_peak_now ? '#DC2626' : '#059669'}
              />
            </View>
            <View style={styles.peakBannerContent}>
              <Text
                style={[
                  styles.peakBannerTitle,
                  { color: peakData.is_peak_now ? '#DC2626' : '#059669' },
                ]}
              >
                {peakData.is_peak_now ? 'Peak Hour Active' : 'Off-Peak Now'}
              </Text>
              <Text style={styles.peakBannerAction}>
                {peakData.suggested_action}
              </Text>
            </View>
          </View>
        )}

        {/* Peak Periods Today */}
        {peakData && peakData.peak_periods_today.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Peak Periods Today</Text>
            {peakData.peak_periods_today.map((period) => {
              const sevConfig: Record<string, string> = {
                HIGH: '#DC2626',
                MEDIUM: '#D97706',
                LOW: '#059669',
              };
              const sevColor = sevConfig[period.severity] ?? '#6B7280';
              return (
                <View key={period.label} style={styles.periodCard}>
                  <View style={styles.periodLeft}>
                    <View style={[styles.periodDot, { backgroundColor: sevColor }]} />
                    <View style={styles.periodContent}>
                      <Text style={styles.periodLabel}>{period.label}</Text>
                      <Text style={styles.periodTime}>
                        {period.start_hour}:00 - {period.end_hour}:00
                      </Text>
                    </View>
                  </View>
                  <View style={styles.periodRight}>
                    <View style={[styles.badge, { backgroundColor: sevColor + '18' }]}>
                      <Text style={[styles.badgeText, { color: sevColor }]}>
                        {period.severity}
                      </Text>
                    </View>
                    <Text style={styles.periodWait}>
                      ~{period.avg_wait_minutes} min wait
                    </Text>
                  </View>
                </View>
              );
            })}
          </View>
        )}

        {/* Best Pickup Slot */}
        {pickupData?.best_slot && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Recommended Pickup Time</Text>
            <View style={styles.bestSlotCard}>
              <View style={styles.bestSlotIcon}>
                <MaterialCommunityIcons name="star-circle" size={28} color="#3B82F6" />
              </View>
              <View style={styles.bestSlotContent}>
                <Text style={styles.bestSlotVendor}>
                  {pickupData.best_slot.vendor_name}
                </Text>
                <Text style={styles.bestSlotTime}>
                  {pickupData.best_slot.start_time} - {pickupData.best_slot.end_time}
                </Text>
                <Text style={styles.bestSlotEta}>
                  ETA: {pickupData.best_slot.eta_minutes} min
                </Text>
              </View>
              <View style={styles.bestSlotBadges}>
                <CongestionBadge level={pickupData.best_slot.congestion_level} />
                <DelayBadge risk={pickupData.best_slot.delay_risk} />
              </View>
            </View>
          </View>
        )}

        {/* Alternative Slots */}
        {pickupData && pickupData.alternative_slots.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Alternative Times</Text>
            {pickupData.alternative_slots.map((slot) => (
              <View key={slot.slot_id} style={styles.altSlotCard}>
                <View style={styles.altSlotContent}>
                  <Text style={styles.altSlotVendor}>{slot.vendor_name}</Text>
                  <Text style={styles.altSlotTime}>
                    {slot.start_time} - {slot.end_time}
                  </Text>
                  <Text style={styles.altSlotEta}>ETA: {slot.eta_minutes} min</Text>
                </View>
                <View style={styles.altSlotBadges}>
                  <CongestionBadge level={slot.congestion_level} />
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Off-Peak Windows */}
        {peakData && peakData.off_peak_windows.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Off-Peak Windows</Text>
            {peakData.off_peak_windows.map((w) => (
              <View key={w.hour} style={styles.offPeakCard}>
                <View style={styles.offPeakIcon}>
                  <MaterialCommunityIcons name="weather-sunny" size={18} color="#059669" />
                </View>
                <View style={styles.offPeakContent}>
                  <Text style={styles.offPeakLabel}>{w.label}</Text>
                  <Text style={styles.offPeakWait}>
                    ~{w.expected_wait_minutes} min wait
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Preferred Hour Info */}
        {pickupData && (
          <View style={styles.prefCard}>
            <MaterialCommunityIcons name="information-outline" size={18} color="#6B7280" />
            <Text style={styles.prefText}>
              Your preferred pickup hour is {pickupData.preferred_hour}:00
              ({pickupData.preferred_hour_source})
            </Text>
          </View>
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: 32,
    gap: 16,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 14,
    color: '#6B7280',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 8,
  },
  backBtn: {
    padding: 4,
  },
  title: {
    fontSize: 22,
    fontWeight: '900',
    color: '#111827',
  },
  errorCard: {
    alignItems: 'center',
    backgroundColor: '#FEF2F2',
    borderRadius: 16,
    padding: 28,
    gap: 10,
    borderWidth: 1,
    borderColor: '#FECACA',
  },
  errorTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#991B1B',
  },
  errorMessage: {
    fontSize: 14,
    color: '#7F1D1D',
    textAlign: 'center',
    lineHeight: 20,
  },
  retryButton: {
    marginTop: 8,
    backgroundColor: '#DC2626',
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 10,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  emptyCard: {
    alignItems: 'center',
    backgroundColor: '#F9FAFB',
    borderRadius: 16,
    padding: 28,
    gap: 10,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#4B5563',
  },
  emptyMessage: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
    lineHeight: 20,
  },
  peakBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 16,
    padding: 16,
    gap: 12,
  },
  peakBannerActive: {
    backgroundColor: '#FEF2F2',
    borderWidth: 1,
    borderColor: '#FECACA',
  },
  peakBannerClear: {
    backgroundColor: '#F0FDF4',
    borderWidth: 1,
    borderColor: '#BBF7D0',
  },
  peakBannerLeft: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  peakBannerContent: {
    flex: 1,
    gap: 2,
  },
  peakBannerTitle: {
    fontSize: 16,
    fontWeight: '800',
  },
  peakBannerAction: {
    fontSize: 13,
    color: '#4B5563',
    lineHeight: 18,
  },
  section: {
    gap: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#111827',
    marginBottom: 4,
  },
  periodCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 4,
    elevation: 2,
  },
  periodLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  periodDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  periodContent: {
    gap: 2,
  },
  periodLabel: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
  },
  periodTime: {
    fontSize: 12,
    color: '#6B7280',
  },
  periodRight: {
    alignItems: 'flex-end',
    gap: 4,
  },
  periodWait: {
    fontSize: 11,
    color: '#9CA3AF',
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  bestSlotCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#EFF6FF',
    borderRadius: 16,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  bestSlotIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: '#DBEAFE',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bestSlotContent: {
    flex: 1,
    gap: 2,
  },
  bestSlotVendor: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1E40AF',
  },
  bestSlotTime: {
    fontSize: 14,
    color: '#1D4ED8',
    fontWeight: '600',
  },
  bestSlotEta: {
    fontSize: 12,
    color: '#6B7280',
  },
  bestSlotBadges: {
    gap: 4,
    alignItems: 'flex-end',
  },
  altSlotCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 4,
    elevation: 2,
  },
  altSlotContent: {
    gap: 2,
  },
  altSlotVendor: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
  },
  altSlotTime: {
    fontSize: 13,
    color: '#374151',
  },
  altSlotEta: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  altSlotBadges: {
    gap: 4,
  },
  offPeakCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F0FDF4',
    borderRadius: 12,
    padding: 12,
    gap: 10,
  },
  offPeakIcon: {
    width: 32,
    height: 32,
    borderRadius: 10,
    backgroundColor: '#DCFCE7',
    alignItems: 'center',
    justifyContent: 'center',
  },
  offPeakContent: {
    gap: 2,
  },
  offPeakLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#166534',
  },
  offPeakWait: {
    fontSize: 12,
    color: '#059669',
  },
  prefCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    padding: 12,
    gap: 8,
  },
  prefText: {
    flex: 1,
    fontSize: 13,
    color: '#6B7280',
  },
});
