// ─── Settlement Dashboard ─────────────────────────────────────────
// Premium financial dashboard with revenue tracking, transactions, refunds,
// and real-time transaction feed with auto-refresh.

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../context/AuthContext';
import { settlementApi } from '../../services/settlementApi';
import { colors as staticColors, shadows, spacing } from '../../design-system';
const colors = staticColors;
import { formatRupees } from '../../utils/format';
import GlassCard from '../../design-system/components/GlassCard';
import StatCard from '../../design-system/components/StatCard';
import RevenueCard from '../../design-system/components/RevenueCard';
import ForecastCard from '../../design-system/components/ForecastCard';
import Badge from '../../design-system/components/Badge';
import { useTheme } from '../../context/ThemeContext';
import { useVendorWebSocket } from '../../hooks/useVendorWebSocket';

type TabType = 'overview' | 'transactions' | 'settlements' | 'refunds' | 'live';

export default function SettlementDashboard({ navigation }: any) {
  const { colors } = useTheme();
  const styles = getStyles(colors);
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<any>(null);
  const { user, token } = useAuth();
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // ── WebSocket live payments ──────────────────────────────────
  const [wsDisconnected, setWsDisconnected] = useState(false);

  const handleWsEvent = useCallback((evt: { event: string; data: any }) => {
    if (evt.event === 'payment_confirmed') {
      loadData(true);
    }
  }, []);

  const { isConnected: wsConnected } = useVendorWebSocket(
    [],
    token ?? null,
    handleWsEvent,
    {
      useVendorChannel: true,
      onDisconnected: () => setWsDisconnected(true),
    }
  );

  useEffect(() => {
    if (wsConnected) {
      setWsDisconnected(false);
    }
  }, [wsConnected]);

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    loadData();
  }, []);

  const loadData = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      const [revRes, txRes, settRes, refRes, dailyRes] = await Promise.all([
        settlementApi.getRevenue(),
        settlementApi.getTransactions(),
        settlementApi.getSettlements(),
        settlementApi.getRefunds(),
        settlementApi.getDailyRevenue(),
      ]);
      setData({
        revenue: revRes.data,
        transactions: txRes.data,
        settlements: settRes.data,
        refunds: refRes.data,
        daily: dailyRes.data,
      });
    } catch (err) {
      console.error('Settlements load error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // R6: Auto-refresh for Live Feed tab (polling every 20s when active AND WebSocket is disconnected)
  const livePollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (activeTab === 'live' && wsDisconnected) {
      // Start polling every 20 seconds when Live Feed is active and WS is disconnected
      livePollRef.current = setInterval(() => {
        loadData(true);
      }, 20_000);
    }
    return () => {
      if (livePollRef.current) {
        clearInterval(livePollRef.current);
        livePollRef.current = null;
      }
    };
  }, [activeTab, wsDisconnected]);

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '📊' },
    { key: 'transactions', label: 'Transactions', icon: '💳' },
    { key: 'settlements', label: 'Settlements', icon: '🏦' },
    { key: 'refunds', label: 'Refunds', icon: '↩️' },
    { key: 'live', label: 'Live Feed', icon: '⚡' },
  ];

  const wallet = data?.revenue?.wallet || {};

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.bg }, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={[styles.loadingText, { color: colors.textMuted }]}>Loading financial data...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.primary }]}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <Text style={[styles.headerTitle, { color: colors.textInverse }]}>Settlements</Text>
        <Text style={[styles.headerSubtitle, { color: 'rgba(255,255,255,0.7)' }]}>Financial overview for {user?.vendor_name}</Text>
      </View>

      {/* Tabs */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabRow} contentContainerStyle={styles.tabContentPad}>
        {tabs.map(tab => (
          <TouchableOpacity
            key={tab.key}
            style={[
              styles.tab,
              { backgroundColor: colors.bgCard, borderColor: colors.border },
              activeTab === tab.key && [styles.tabActive, { backgroundColor: colors.primary, borderColor: colors.primary }]
            ]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Text style={styles.tabIcon}>{tab.icon}</Text>
            <Text style={[
              styles.tabText,
              { color: colors.textSecondary },
              activeTab === tab.key && [styles.tabTextActive, { color: colors.textInverse }]
            ]} numberOfLines={1}>{tab.label}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(true); }} tintColor={colors.primary} />}
        style={styles.scrollContent}
      >
        {/* Overview */}
        {activeTab === 'overview' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <RevenueCard
              title="Current Balance"
              amount={wallet.current_balance || 0}
              subtitle="Available for settlement"
              icon="💰"
              color={colors.success}
              data={(data?.daily?.daily_revenue || []).slice(-7).map((d: any) => ({
                value: d.net,
                label: d.day_name?.slice(0, 3) || 'Day',
              }))}
              style={{ marginBottom: spacing.md }}
            />
            <View style={styles.statsRow}>
              <StatCard value={wallet.total_earned || 0} label="Total Earned" prefix="₹" color={colors.success} style={{ flexBasis: '45%', flexGrow: 1 }} format="currency" />
              <StatCard value={wallet.total_pending || 0} label="Pending" prefix="₹" color={colors.warning} style={{ flexBasis: '45%', flexGrow: 1 }} format="currency" />
            </View>
            <ForecastCard
              title="Wallet Summary"
              icon="🏦"
              color={colors.primary}
              data={[
                { label: 'Total Earned', value: wallet.total_earned || 0, unit: '₹' },
                { label: 'Pending Settlement', value: wallet.total_pending || 0, unit: '₹', trend: (wallet.total_pending || 0) > 0 ? 'up' : 'stable' },
                { label: 'Settled', value: wallet.total_settled || 0, unit: '₹' },
                { label: 'Total Refunded', value: wallet.total_refunded || 0, unit: '₹', trend: (wallet.total_refunded || 0) > 0 ? 'down' : 'stable' },
              ]}
              style={{ marginBottom: spacing.md }}
            />
            {data?.revenue?.today && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Today's Revenue</Text>
                <View style={styles.todayGrid}>
                  <View style={[styles.todayCard, { backgroundColor: colors.bgSecondary }]}>
                    <Text style={[styles.todayValue, { color: colors.textPrimary }]}>{formatRupees(data.revenue.today.online_payments || 0)}</Text>
                    <Text style={[styles.todayLabel, { color: colors.textMuted }]}>Online</Text>
                  </View>
                  <View style={[styles.todayCard, { backgroundColor: colors.bgSecondary }]}>
                    <Text style={[styles.todayValue, { color: colors.error }]}>{formatRupees(data.revenue.today.refunds || 0)}</Text>
                    <Text style={[styles.todayLabel, { color: colors.textMuted }]}>Refunds</Text>
                  </View>
                  <View style={[styles.todayCard, { backgroundColor: colors.bgSecondary }]}>
                    <Text style={[styles.todayValue, { color: colors.success }]}>{formatRupees(data.revenue.today.net_revenue || 0)}</Text>
                    <Text style={[styles.todayLabel, { color: colors.textMuted }]}>Net</Text>
                  </View>
                </View>
              </GlassCard>
            )}
          </Animated.View>
        )}

        {/* Transactions */}
        {activeTab === 'transactions' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            {data?.transactions?.summary && (
              <View style={styles.statsRow}>
                <StatCard value={data.transactions.summary.total_online || 0} label="Online" prefix="₹" color={colors.info} style={{ flexBasis: '45%', flexGrow: 1 }} format="currency" />
                <StatCard value={data.transactions.summary.total_refunds || 0} label="Refunds" prefix="₹" color={colors.error} style={{ flexBasis: '45%', flexGrow: 1 }} format="currency" />
              </View>
            )}
            <GlassCard padding={16} borderRadius={20}>
              <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Recent Transactions</Text>
              {(data?.transactions?.transactions || []).slice(0, 10).map((tx: any, i: number) => (
                <View key={i} style={[styles.txRow, { borderBottomColor: colors.borderLight }]}>
                  <View style={[styles.txIcon, { backgroundColor: colors.bgSecondary }]}>
                    <Text style={styles.txEmoji}>
                      {tx.type === 'online_payment' ? '💳' : tx.type === 'cash_order' ? '💵' : '↩️'}
                    </Text>
                  </View>
                  <View style={styles.txInfo}>
                    <Text style={[styles.txDesc, { color: colors.textPrimary }]}>{tx.description}</Text>
                    <Text style={[styles.txDate, { color: colors.textMuted }]}>{tx.created_at ? new Date(tx.created_at).toLocaleDateString() : '—'}</Text>
                  </View>
                  <View style={styles.txAmount}>
                    <Text style={[styles.txAmountText, { color: tx.type === 'refund' ? colors.error : colors.success }]}>
                      {tx.type === 'refund' ? '-' : '+'}{formatRupees(tx.amount)}
                    </Text>
                    {tx.fee > 0 && <Text style={[styles.txFee, { color: colors.textMuted }]}>Fee: {formatRupees(tx.fee)}</Text>}
                  </View>
                </View>
              ))}
            </GlassCard>
          </Animated.View>
        )}

        {/* Settlements */}
        {activeTab === 'settlements' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
              <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>🏦 Settlement Status</Text>
              <View style={styles.settlementStats}>
                <View style={styles.settlementStat}>
                  <Text style={[styles.settStatValue, { color: colors.textPrimary }]}>{formatRupees(data?.settlements?.wallet?.balance || 0)}</Text>
                  <Text style={[styles.settStatLabel, { color: colors.textMuted }]}>Balance</Text>
                </View>
                <View style={styles.settlementStat}>
                  <Text style={[styles.settStatValue, { color: colors.warning }]}>{formatRupees(data?.settlements?.wallet?.pending || 0)}</Text>
                  <Text style={[styles.settStatLabel, { color: colors.textMuted }]}>Pending</Text>
                </View>
                <View style={styles.settlementStat}>
                  <Text style={[styles.settStatValue, { color: colors.success }]}>{formatRupees(data?.settlements?.wallet?.settled || 0)}</Text>
                  <Text style={[styles.settStatLabel, { color: colors.textMuted }]}>Settled</Text>
                </View>
              </View>
            </GlassCard>
            {(data?.settlements?.settlements || []).length > 0 && (
              <GlassCard padding={16} borderRadius={20}>
                <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Settlement History</Text>
                {data.settlements.settlements.map((s: any, i: number) => (
                  <View key={i} style={[styles.settRow, { borderBottomColor: colors.borderLight }]}>
                    <View style={styles.settHeader}>
                      <Text style={[styles.settPeriod, { color: colors.textPrimary }]}>{s.period}</Text>
                      <View style={[styles.statusBadge, { backgroundColor: s.status === 'completed' ? colors.successPale : s.status === 'pending' ? colors.warningPale : colors.bgTertiary }]}>
                        <Text style={[styles.statusText, { color: s.status === 'completed' ? colors.successDark : s.status === 'pending' ? colors.warningDark : colors.textSecondary }]}>
                          {s.status}
                        </Text>
                      </View>
                    </View>
                    <Text style={[styles.settDetail, { color: colors.textSecondary }]}>Orders: {s.order_count} · Online: {formatRupees(s.online_payments)} · Refunds: {formatRupees(s.refunds)}</Text>
                    <View style={[styles.settTotalRow, { borderTopColor: colors.borderLight }]}>
                      <Text style={[styles.settTotalLabel, { color: colors.textSecondary }]}>Net Amount</Text>
                      <Text style={styles.settTotalValue}>{formatRupees(s.net_amount)}</Text>
                    </View>
                  </View>
                ))}
              </GlassCard>
            )}
          </Animated.View>
        )}

        {/* Live Feed — Real-time Transaction Stream */}
        {activeTab === 'live' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <View style={styles.statsRow}>
              <StatCard value={data?.transactions?.total_transactions || 0} label="Total Tx" icon="📊" color={colors.primary} style={{ flex: 1 }} />
              <StatCard value={data?.transactions?.summary?.net_revenue || 0} label="Net Revenue" prefix="₹" color={colors.success} style={{ flex: 1 }} format="currency" />
            </View>
            <GlassCard padding={16} borderRadius={20}>
              <View style={[styles.liveHeader, { borderBottomColor: colors.borderLight }]}>
                <View style={styles.liveHeaderLeft}>
                  <View style={[styles.liveDot, { backgroundColor: colors.success }]} />
                  <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Live Transaction Feed</Text>
                </View>
                <Text style={[styles.liveCount, { color: colors.textMuted }]}>
                  {(data?.transactions?.transactions || []).length} transactions
                </Text>
              </View>
              <Text style={[styles.sectionSubtitle, { color: colors.textMuted }]}>
                Auto-refreshes every 15s · Most recent first
              </Text>
              {(data?.transactions?.transactions || []).slice(0, 20).map((tx: any, i: number) => {
                const isPayment = tx.type === 'online_payment';
                const isCash = tx.type === 'cash_order';
                const isRefund = tx.type === 'refund';
                const icon = isPayment ? '💳' : isCash ? '💵' : '↩️';
                const amountColor = isRefund ? colors.error : colors.success;
                const sign = isRefund ? '-' : '+';
                return (
                  <View key={i} style={[styles.liveTxRow, { borderBottomColor: colors.borderLight }]}>
                    <View style={[styles.liveTxIcon, { backgroundColor: isRefund ? colors.errorPale : colors.successPale }]}>
                      <Text style={styles.liveTxEmoji}>{icon}</Text>
                    </View>
                    <View style={styles.liveTxInfo}>
                      <Text style={[styles.liveTxDesc, { color: colors.textPrimary }]}>{tx.description}</Text>
                      <View style={styles.liveTxMeta}>
                        <Badge label={tx.payment_method || tx.type} variant={isRefund ? 'error' : 'success'} size="sm" />
                        {tx.fee > 0 && (
                          <Text style={[styles.liveTxFee, { color: colors.textMuted }]}>Fee: {formatRupees(tx.fee)}</Text>
                        )}
                      </View>
                    </View>
                    <View style={styles.liveTxAmount}>
                      <Text style={[styles.liveTxAmountText, { color: amountColor }]}>
                        {sign}{formatRupees(tx.amount)}
                      </Text>
                      {tx.net_amount && (
                        <Text style={[styles.liveTxNet, { color: colors.textMuted }]}>
                          Net: {formatRupees(tx.net_amount)}
                        </Text>
                      )}
                    </View>
                  </View>
                );
              })}
              {(data?.transactions?.transactions || []).length === 0 && (
                <View style={styles.liveEmpty}>
                  <Text style={styles.liveEmptyIcon}>⚡</Text>
                  <Text style={[styles.liveEmptyText, { color: colors.textMuted }]}>No recent transactions</Text>
                </View>
              )}
            </GlassCard>
          </Animated.View>
        )}

        {/* Refunds */}
        {activeTab === 'refunds' && (
          <Animated.View style={{ opacity: fadeAnim }}>
            <View style={styles.statsRow}>
              <StatCard value={data?.refunds?.total_refunds || 0} label="Total Refunds" icon="↩️" color={colors.error} style={{ flexBasis: '45%', flexGrow: 1 }} />
              <StatCard value={data?.refunds?.total_refunded_amount || 0} label="Amount Refunded" prefix="₹" color={colors.warning} style={{ flexBasis: '45%', flexGrow: 1 }} format="currency" />
            </View>
            <ForecastCard
              title="Refund Analysis"
              icon="↩️"
              color={colors.error}
              data={[
                { label: 'Total Refunds', value: data?.refunds?.total_refunds || 0 },
                { label: 'Amount Refunded', value: data?.refunds?.total_refunded_amount || 0, unit: '₹' },
                { label: 'Refund Rate', value: data?.refunds?.refund_rate || 0, unit: '%', trend: (data?.refunds?.refund_rate || 0) > 5 ? 'up' : 'stable' },
              ]}
              style={{ marginBottom: spacing.md }}
            />
            {(data?.refunds?.refunds || []).length > 0 && (
              <GlassCard padding={16} borderRadius={20}>
                <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Recent Refunds</Text>
                {data.refunds.refunds.slice(0, 10).map((refund: any, i: number) => (
                  <View key={i} style={[styles.refundRow, { borderBottomColor: colors.borderLight }]}>
                    <View style={styles.refundInfo}>
                      <Text style={[styles.refundOrder, { color: colors.textPrimary }]}>Order #{refund.order_id}</Text>
                      <Text style={[styles.refundDate, { color: colors.textMuted }]}>{refund.created_at ? new Date(refund.created_at).toLocaleDateString() : '—'}</Text>
                    </View>
                    <View style={styles.refundAmount}>
                      <Text style={styles.refundAmountText}>-{formatRupees(refund.amount)}</Text>
                      <Badge label={refund.status} variant={refund.status === 'processed' ? 'success' : 'warning'} size="sm" />
                    </View>
                  </View>
                ))}
              </GlassCard>
            )}
          </Animated.View>
        )}
        <View style={{ height: 100 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const getStyles = (colors: any) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  tabRow: { height: 75, maxHeight: 75, marginTop: 8, marginBottom: 4 },
  tabContentPad: { paddingHorizontal: spacing.lg, gap: spacing.sm, paddingVertical: 12 },
  scrollContent: { flex: 1, paddingHorizontal: spacing.lg, paddingTop: 12, paddingBottom: 24 },
  tab: {
    flexDirection: 'row', alignItems: 'center', paddingHorizontal: 22, paddingVertical: 10,
    borderRadius: 14, backgroundColor: colors.bgCard, marginRight: 8, gap: 6,
    borderWidth: 1.5, borderColor: colors.border, ...shadows.sm,
  },
  tabActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  tabIcon: { fontSize: 14 },
  tabText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary },
  tabTextActive: { color: colors.textInverse },
  statsRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: 12 },
  todayGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  todayCard: { flex: 1, minWidth: '45%', backgroundColor: colors.bgSecondary, borderRadius: 10, padding: 12, alignItems: 'center' },
  todayValue: { fontSize: 18, fontWeight: '700', color: colors.textPrimary },
  todayLabel: { fontSize: 11, color: colors.textMuted, marginTop: 4, fontWeight: '600' },
  txRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.borderLight, gap: 10 },
  txIcon: { width: 36, height: 36, borderRadius: 12, backgroundColor: colors.bgTertiary, justifyContent: 'center', alignItems: 'center' },
  txEmoji: { fontSize: 16 },
  txInfo: { flex: 1 },
  txDesc: { fontSize: 14, fontWeight: '500', color: colors.textPrimary },
  txDate: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  txAmount: { alignItems: 'flex-end' },
  txAmountText: { fontSize: 14, fontWeight: '700' },
  txFee: { fontSize: 11, color: colors.textMuted, marginTop: 2 },
  settlementStats: { flexDirection: 'row', gap: 8 },
  settlementStat: { flex: 1, alignItems: 'center' },
  settStatValue: { fontSize: 20, fontWeight: '700', color: colors.textPrimary },
  settStatLabel: { fontSize: 11, color: colors.textMuted, marginTop: 4 },
  settRow: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: colors.borderLight },
  settHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  settPeriod: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  statusText: { fontSize: 10, fontWeight: '600' },
  settDetail: { fontSize: 12, color: colors.textSecondary, marginBottom: 6 },
  settTotalRow: { flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: colors.borderLight, paddingTop: 6 },
  settTotalLabel: { fontSize: 14, fontWeight: '600', color: colors.textSecondary },
  settTotalValue: { fontSize: 16, fontWeight: '700', color: colors.success },
  refundRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.borderLight },
  refundInfo: { flex: 1 },
  refundOrder: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  refundDate: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  refundAmount: { alignItems: 'flex-end', gap: 4 },
  refundAmountText: { fontSize: 16, fontWeight: '700', color: colors.error },

  // ── Live Feed styles ──────────────────────────────────────────
  liveHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingBottom: 8, borderBottomWidth: 1, marginBottom: 8,
  },
  liveHeaderLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  liveDot: { width: 8, height: 8, borderRadius: 4 },
  liveCount: { fontSize: 12, fontWeight: '600' },
  sectionSubtitle: { fontSize: 12, marginBottom: spacing.md },
  liveTxRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: 8, gap: 10,
    borderBottomWidth: 1,
  },
  liveTxIcon: { width: 32, height: 32, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  liveTxEmoji: { fontSize: 14 },
  liveTxInfo: { flex: 1 },
  liveTxDesc: { fontSize: 13, fontWeight: '500' },
  liveTxMeta: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 },
  liveTxFee: { fontSize: 11 },
  liveTxAmount: { alignItems: 'flex-end' },
  liveTxAmountText: { fontSize: 14, fontWeight: '700' },
  liveTxNet: { fontSize: 11, marginTop: 2 },
  liveEmpty: { alignItems: 'center', paddingVertical: 24, gap: 8 },
  liveEmptyIcon: { fontSize: 32 },
  liveEmptyText: { fontSize: 14 },
});
