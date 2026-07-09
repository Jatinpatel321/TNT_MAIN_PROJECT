import React, { useEffect, useMemo, useState } from 'react';
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
import type { AppTabsParamList, RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { getPoints, getAvailableRedemptions, getVouchers } from '../../services/rewardsService';
import type { UserPoints, RedemptionRule, Voucher, RewardTypeKey } from '../../types/models';
import { toApiError } from '../../services/apiClient';
import { useAppTheme } from '../../theme/ThemeContext';
import type { AppPalette } from '../../theme/theme';

type Props = NativeStackScreenProps<AppTabsParamList & RootStackParamList, 'RewardsTab'>;

const REWARD_ICONS: Record<RewardTypeKey, { icon: string; color: string }> = {
  order_completion: { icon: 'check-circle', color: '#059669' },
  first_order: { icon: 'party-popper', color: '#7C3AED' },
  referral: { icon: 'account-plus', color: '#2563EB' },
  loyalty_milestone: { icon: 'trophy', color: '#D97706' },
  off_peak_bonus: { icon: 'clock-outline', color: '#0891B2' },
  voucher_redemption: { icon: 'ticket-percent', color: '#DC2626' },
};

function getTier(points: number): { name: string; color: string; min: number; max: number } {
  if (points >= 2000) return { name: 'Platinum', color: '#6B7280', min: 2000, max: Infinity };
  if (points >= 1000) return { name: 'Gold', color: '#D97706', min: 1000, max: 2000 };
  if (points >= 500) return { name: 'Silver', color: '#6B7280', min: 500, max: 1000 };
  return { name: 'Bronze', color: '#92400E', min: 0, max: 500 };
}

export function RewardsScreen({ navigation }: Props) {
  const { colors } = useAppTheme();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  const [points, setPoints] = useState<UserPoints | null>(null);
  const [redemptions, setRedemptions] = useState<RedemptionRule[]>([]);
  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const [p, r, v] = await Promise.all([
        getPoints(),
        getAvailableRedemptions(),
        getVouchers(),
      ]);
      setPoints(p);
      setRedemptions(r);
      setVouchers(v);
    } catch (e) {
      // silent
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
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </Screen>
    );
  }

  const currentPoints = points?.current_points ?? 0;
  const tier = getTier(currentPoints);
  const tierProgress = tier.max === Infinity ? 1 : (currentPoints - tier.min) / (tier.max - tier.min);

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Text style={styles.title}>Rewards</Text>
        </View>

        {/* Points Balance Card */}
        <View style={styles.balanceCard}>
          <View style={styles.balanceTop}>
            <View>
              <Text style={styles.balanceLabel}>Available Points</Text>
              <Text style={styles.balanceNumber}>{Math.floor(currentPoints)}</Text>
            </View>
            <View style={[styles.tierBadge, { backgroundColor: tier.color + '18' }]}>
              <MaterialCommunityIcons name="trophy" size={16} color={tier.color} />
              <Text style={[styles.tierText, { color: tier.color }]}>{tier.name}</Text>
            </View>
          </View>

          <View style={styles.tierProgressBar}>
            <View style={[styles.tierProgressFill, { width: `${tierProgress * 100}%`, backgroundColor: tier.color }]} />
          </View>
          <Text style={styles.tierProgressLabel}>
            {tier.max === Infinity
              ? 'Max tier reached!'
              : `${Math.floor(tier.max - currentPoints)} pts to ${getTier(tier.max).name}`}
          </Text>

          <View style={styles.statsRow}>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{Math.floor(points?.total_earned ?? 0)}</Text>
              <Text style={styles.statLabel}>Earned</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{Math.floor(points?.total_redeemed ?? 0)}</Text>
              <Text style={styles.statLabel}>Redeemed</Text>
            </View>
          </View>
        </View>

        {/* Recent Activity */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Recent Activity</Text>
            <Pressable onPress={() => navigation.navigate('RedemptionHistory' as any)}>
              <Text style={styles.seeAll}>See All</Text>
            </Pressable>
          </View>

          {(points?.recent_transactions ?? []).length === 0 &&
          (points?.recent_redemptions ?? []).length === 0 ? (
            <View style={styles.emptyState}>
              <MaterialCommunityIcons name="star-outline" size={40} color={colors.muted} />
              <Text style={styles.emptyText}>No activity yet. Place an order to start earning!</Text>
            </View>
          ) : (
            <>
              {(points?.recent_transactions ?? []).slice(0, 5).map((t) => {
                const config = REWARD_ICONS[t.reward_type] ?? REWARD_ICONS.order_completion;
                return (
                  <View key={`t-${t.id}`} style={styles.activityRow}>
                    <View style={[styles.activityIcon, { backgroundColor: config.color + '15' }]}>
                      <MaterialCommunityIcons name={config.icon as any} size={18} color={config.color} />
                    </View>
                    <View style={styles.activityContent}>
                      <Text style={styles.activityDesc}>{t.description}</Text>
                      <Text style={styles.activityDate}>
                        {new Date(t.created_at).toLocaleDateString()}
                      </Text>
                    </View>
                    <Text style={styles.activityPoints}>+{Math.floor(t.points)}</Text>
                  </View>
                );
              })}
              {(points?.recent_redemptions ?? []).slice(0, 3).map((r) => (
                <View key={`r-${r.id}`} style={styles.activityRow}>
                  <View style={[styles.activityIcon, { backgroundColor: '#FEE2E2' }]}>
                    <MaterialCommunityIcons name="minus-circle" size={18} color="#DC2626" />
                  </View>
                  <View style={styles.activityContent}>
                    <Text style={styles.activityDesc}>{r.description}</Text>
                    <Text style={styles.activityDate}>
                      {new Date(r.created_at).toLocaleDateString()}
                    </Text>
                  </View>
                  <Text style={styles.activityPointsRedeemed}>-{Math.floor(r.points_used)}</Text>
                </View>
              ))}
            </>
          )}
        </View>

        {/* Available Redemptions */}
        {redemptions.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Redeem Points</Text>
            {redemptions.map((rule) => (
              <View key={rule.id} style={styles.redemptionCard}>
                <View style={styles.redemptionInfo}>
                  <Text style={styles.redemptionType}>
                    {rule.redemption_type === 'discount_percentage'
                      ? 'Percentage Discount'
                      : rule.redemption_type === 'discount_fixed'
                        ? 'Fixed Discount'
                        : 'Free Item'}
                  </Text>
                  <Text style={styles.redemptionMin}>
                    Min {Math.floor(rule.min_points)} pts
                  </Text>
                </View>
                {currentPoints >= rule.min_points ? (
                  <View style={styles.redeemAvailable}>
                    <MaterialCommunityIcons name="check-circle" size={16} color="#059669" />
                    <Text style={styles.redeemAvailableText}>Available</Text>
                  </View>
                ) : (
                  <Text style={styles.redeemLocked}>
                    Need {Math.floor(rule.min_points - currentPoints)} more
                  </Text>
                )}
              </View>
            ))}
          </View>
        )}

        {/* Active Vouchers */}
        {vouchers.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Active Vouchers</Text>
            {vouchers.map((v) => (
              <View key={v.id} style={styles.voucherCard}>
                <View style={styles.voucherLeft}>
                  <MaterialCommunityIcons name="ticket-percent" size={24} color="#3B82F6" />
                </View>
                <View style={styles.voucherContent}>
                  <Text style={styles.voucherCode}>{v.code}</Text>
                  <Text style={styles.voucherDesc}>{v.description}</Text>
                  <Text style={styles.voucherExpiry}>
                    Expires {new Date(v.expires_at).toLocaleDateString()}
                  </Text>
                </View>
                <View style={styles.voucherValue}>
                  <Text style={styles.voucherValueText}>
                    {v.discount_type === 'percentage'
                      ? `${v.discount_value}%`
                      : `Rs ${v.discount_value}`}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </Screen>
  );
}

const makeStyles = (colors: AppPalette) => StyleSheet.create({
  scroll: {
    paddingBottom: 32,
    gap: 16,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    paddingVertical: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: '900',
    color: colors.text,
  },
  balanceCard: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    padding: 20,
    gap: 12,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 8,
    elevation: 4,
  },
  balanceTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  balanceLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.muted,
  },
  balanceNumber: {
    fontSize: 36,
    fontWeight: '900',
    color: colors.text,
    marginTop: 2,
  },
  tierBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  tierText: {
    fontSize: 13,
    fontWeight: '800',
  },
  tierProgressBar: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.surfaceAlt,
    overflow: 'hidden',
  },
  tierProgressFill: {
    height: '100%',
    borderRadius: 3,
  },
  tierProgressLabel: {
    fontSize: 11,
    color: colors.muted,
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.text,
  },
  statLabel: {
    fontSize: 12,
    color: colors.muted,
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    height: 28,
    backgroundColor: colors.border,
  },
  section: {
    gap: 10,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.text,
  },
  seeAll: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.primary,
  },
  emptyState: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    gap: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  emptyText: {
    fontSize: 14,
    color: colors.muted,
    textAlign: 'center',
  },
  activityRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 12,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 4,
    elevation: 2,
  },
  activityIcon: {
    width: 34,
    height: 34,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  activityContent: {
    flex: 1,
    gap: 2,
  },
  activityDesc: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.text,
  },
  activityDate: {
    fontSize: 11,
    color: colors.muted,
  },
  activityPoints: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.success,
  },
  activityPointsRedeemed: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.danger,
  },
  redemptionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 4,
    elevation: 2,
  },
  redemptionInfo: {
    gap: 2,
  },
  redemptionType: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.text,
  },
  redemptionMin: {
    fontSize: 12,
    color: colors.muted,
  },
  redeemAvailable: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: colors.successSoft,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
  },
  redeemAvailableText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.success,
  },
  redeemLocked: {
    fontSize: 12,
    color: colors.muted,
    fontWeight: '600',
  },
  voucherCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 14,
    gap: 12,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 4,
    elevation: 2,
  },
  voucherLeft: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  voucherContent: {
    flex: 1,
    gap: 2,
  },
  voucherCode: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.text,
  },
  voucherDesc: {
    fontSize: 12,
    color: colors.muted,
  },
  voucherExpiry: {
    fontSize: 11,
    color: colors.muted,
  },
  voucherValue: {
    backgroundColor: colors.primary,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 10,
  },
  voucherValueText: {
    fontSize: 13,
    fontWeight: '800',
    color: colors.onPrimary,
  },
});
