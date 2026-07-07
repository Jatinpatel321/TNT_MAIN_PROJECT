// ─── Loyalty Points Management ─────────────────────────────────
// Vendor-facing rewards & loyalty screen
// Consumes backend rewards endpoints (existing at /v1/rewards/*)

import React, {useCallback, useEffect, useRef, useState} from 'react';
import {
  ActivityIndicator,
  Animated,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import {vendorApi} from '../../services/vendorApi';
import {colors, shadows, spacing} from '../../design-system';
import {formatPaise, formatRupees} from '../../utils/format';
import GlassCard from '../../design-system/components/GlassCard';
import StatCard from '../../design-system/components/StatCard';
import Badge from '../../design-system/components/Badge';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';
import {useTheme} from '../../context/ThemeContext';

interface Voucher {
  id: number;
  code: string;
  description: string;
  discount_type: string;
  discount_value: number;
  min_order_amount_paise: number;
  max_discount_amount_paise: number | null;
  usage_limit: number | null;
  times_redeemed: number;
  expires_at: string;
  is_active: boolean;
}

interface RedemptionRule {
  id: number;
  redemption_type: string;
  min_points: number;
  max_discount_percentage: number | null;
  max_discount_amount: number | null;
}

type Tab = 'vouchers' | 'rules';

export default function LoyaltyPointsScreen() {
  const {colors: themeColors} = useTheme();
  const [activeTab, setActiveTab] = useState<Tab>('vouchers');
  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [rules, setRules] = useState<RedemptionRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {toValue: 1, duration: 400, useNativeDriver: true}).start();
    loadData();
  }, []);

  const loadData = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      const [vouchersRes, rulesRes] = await Promise.all([
        vendorApi.getVoucherList(),
        vendorApi.getRewardRules(),
      ]);
      setVouchers(Array.isArray(vouchersRes.data) ? vouchersRes.data : []);
      setRules(Array.isArray(rulesRes.data) ? rulesRes.data : []);
    } catch (err) {
      console.error('Failed to load loyalty data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadData(true);
  };

  const activeVouchers = vouchers.filter(v => v.is_active);
  const usedVouchers = vouchers.filter(v => !v.is_active);
  const activeRules = rules.filter(r => r.min_points > 0);

  if (loading) {
    return (
      <View style={[styles.container, {backgroundColor: themeColors.bg}, styles.centered]}>
        <ActivityIndicator size="large" color={themeColors.primary} />
        <Text style={[styles.loadingText, {color: themeColors.textMuted}]}>Loading loyalty data...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.container, {backgroundColor: themeColors.bg}]}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={themeColors.primary} />}>
      {/* Header */}
      <View style={[styles.header, {backgroundColor: themeColors.primary}]}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <Text style={[styles.headerTitle, {color: themeColors.textInverse}]}>Loyalty & Rewards</Text>
        <Text style={[styles.headerSubtitle, {color: 'rgba(255,255,255,0.7)'}]}>
          {activeVouchers.length} active vouchers · {activeRules.length} reward tiers
        </Text>
      </View>

      <Animated.View style={{opacity: fadeAnim, padding: spacing.lg}}>
        {/* Summary */}
        <View style={styles.statsRow}>
          <StatCard value={activeVouchers.length} label="Active Vouchers" icon="🎫" color={themeColors.primary} size="sm" style={{flex: 1}} />
          <StatCard value={activeRules.length} label="Reward Tiers" icon="🏆" color={themeColors.success} size="sm" style={{flex: 1}} />
          <StatCard value={usedVouchers.length} label="Expired/Used" icon="📋" color={themeColors.textMuted} size="sm" style={{flex: 1}} />
        </View>

        {/* Tabs */}
        <View style={styles.tabRow}>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'vouchers' && styles.tabActive, {borderColor: themeColors.border}]}
            onPress={() => setActiveTab('vouchers')}>
            <Text style={[styles.tabText, activeTab === 'vouchers' && styles.tabTextActive, {color: activeTab === 'vouchers' ? themeColors.textInverse : themeColors.textSecondary}]}>
              Vouchers
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'rules' && styles.tabActive, {borderColor: themeColors.border}]}
            onPress={() => setActiveTab('rules')}>
            <Text style={[styles.tabText, activeTab === 'rules' && styles.tabTextActive, {color: activeTab === 'rules' ? themeColors.textInverse : themeColors.textSecondary}]}>
              Redemption Rules
            </Text>
          </TouchableOpacity>
        </View>

        {/* Vouchers */}
        {activeTab === 'vouchers' && (
          <View>
            {activeVouchers.length > 0 && (
              <View style={{marginBottom: spacing.md}}>
                <Text style={[styles.sectionLabel, {color: themeColors.textPrimary}]}>🎫 Active Vouchers</Text>
                {activeVouchers.map((v, i) => (
                  <GlassCard key={`v-${i}`} padding={14} borderRadius={18} style={{marginBottom: spacing.sm}}>
                    <View style={styles.voucherHeader}>
                      <View>
                        <Badge label={v.code} variant="primary" size="sm" />
                      </View>
                      <Badge label={v.discount_type === 'fixed' ? formatPaise(v.discount_value) : `${v.discount_value}%`} variant="success" size="sm" />
                    </View>
                    <Text style={[styles.voucherDesc, {color: themeColors.textPrimary}]}>{v.description}</Text>
                    <View style={styles.voucherMeta}>
                      <View style={styles.metaItem}>
                        <Text style={[styles.metaLabel, {color: themeColors.textMuted}]}>Used</Text>
                        <Text style={[styles.metaValue, {color: themeColors.textPrimary}]}>{v.times_redeemed}{v.usage_limit ? ` / ${v.usage_limit}` : ''}</Text>
                      </View>
                      <View style={styles.metaItem}>
                        <Text style={[styles.metaLabel, {color: themeColors.textMuted}]}>Min Order</Text>
                        <Text style={[styles.metaValue, {color: themeColors.textPrimary}]}>{formatPaise(v.min_order_amount_paise)}</Text>
                      </View>
                      <View style={styles.metaItem}>
                        <Text style={[styles.metaLabel, {color: themeColors.textMuted}]}>Expires</Text>
                        <Text style={[styles.metaValue, {color: themeColors.warning}]}>
                          {v.expires_at ? new Date(v.expires_at).toLocaleDateString() : '—'}
                        </Text>
                      </View>
                    </View>
                  </GlassCard>
                ))}
              </View>
            )}
            {usedVouchers.length > 0 && (
              <View>
                <Text style={[styles.sectionLabel, {color: themeColors.textMuted}]}>Inactive / Expired</Text>
                {usedVouchers.map((v, i) => (
                  <GlassCard key={`uv-${i}`} padding={12} borderRadius={16} intensity="medium" style={{marginBottom: spacing.sm}}>
                    <View style={styles.voucherHeader}>
                      <Text style={[styles.voucherCode, {color: themeColors.textMuted}]}>{v.code}</Text>
                      <Badge label="Inactive" variant="neutral" size="sm" />
                    </View>
                    <Text style={[styles.voucherDesc, {color: themeColors.textSecondary}]}>{v.description}</Text>
                  </GlassCard>
                ))}
              </View>
            )}
            {vouchers.length === 0 && (
              <PremiumEmptyState icon="🎫" title="No Vouchers" description="No reward vouchers found. Vouchers are created by the admin." />
            )}
          </View>
        )}

        {/* Redemption Rules */}
        {activeTab === 'rules' && (
          <View>
            <Text style={[styles.sectionLabel, {color: themeColors.textPrimary}]}>🏆 Redemption Rules</Text>
            <Text style={[styles.sectionSubtitle, {color: themeColors.textMuted}]}>Points-based reward tiers available to customers</Text>
            {activeRules.length > 0 ? activeRules.map((rule, i) => (
              <GlassCard key={`r-${i}`} padding={14} borderRadius={18} style={{marginBottom: spacing.sm}}>
                <View style={styles.ruleHeader}>
                  <Badge label={rule.redemption_type.replace(/_/g, ' ').toUpperCase()} variant="premium" size="sm" />
                  <Text style={[styles.rulePoints, {color: themeColors.warning}]}>Min {rule.min_points} pts</Text>
                </View>
                <View style={styles.ruleMeta}>
                  {rule.max_discount_percentage && (
                    <View style={styles.metaItem}>
                      <Text style={[styles.metaLabel, {color: themeColors.textMuted}]}>Max %</Text>
                      <Text style={[styles.metaValue, {color: themeColors.textPrimary}]}>{rule.max_discount_percentage}%</Text>
                    </View>
                  )}
                  {rule.max_discount_amount && (
                    <View style={styles.metaItem}>
                      <Text style={[styles.metaLabel, {color: themeColors.textMuted}]}>Max</Text>
                      <Text style={[styles.metaValue, {color: themeColors.textPrimary}]}>{formatRupees(rule.max_discount_amount)}</Text>
                    </View>
                  )}
                </View>
              </GlassCard>
            )) : (
              <PremiumEmptyState icon="🏆" title="No Rules" description="No redemption rules configured. Rules are set up by the admin." />
            )}
          </View>
        )}

        <View style={{height: 100}} />
      </Animated.View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1},
  centered: {justifyContent: 'center', alignItems: 'center'},
  loadingText: {marginTop: 12, fontSize: 14, fontWeight: '600'},
  header: {
    paddingTop: spacing.huge + 20,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    overflow: 'hidden',
  },
  headerDeco1: {position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)'},
  headerDeco2: {position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)'},
  headerTitle: {fontSize: 28, fontWeight: '700', letterSpacing: -0.3},
  headerSubtitle: {fontSize: 14, marginTop: 4},
  statsRow: {flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md},
  tabRow: {flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md},
  tab: {flex: 1, paddingVertical: 10, borderRadius: 12, alignItems: 'center', borderWidth: 1.5},
  tabActive: {backgroundColor: colors.primary, borderColor: colors.primary},
  tabText: {fontSize: 13, fontWeight: '600'},
  tabTextActive: {color: colors.textInverse},
  sectionLabel: {fontSize: 16, fontWeight: '700', marginBottom: spacing.sm},
  sectionSubtitle: {fontSize: 12, marginBottom: spacing.md, marginTop: -8},
  voucherHeader: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8},
  voucherCode: {fontSize: 14, fontWeight: '700'},
  voucherDesc: {fontSize: 13, marginBottom: 8, lineHeight: 18},
  voucherMeta: {flexDirection: 'row', gap: 12},
  metaItem: {flex: 1},
  metaLabel: {fontSize: 10},
  metaValue: {fontSize: 13, fontWeight: '600', marginTop: 2},
  ruleHeader: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8},
  rulePoints: {fontSize: 16, fontWeight: '700'},
  ruleMeta: {flexDirection: 'row', gap: 12},
});
