import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { settlementApi } from '../../services/settlementApi';

type TabType = 'overview' | 'transactions' | 'settlements' | 'refunds';

export default function SettlementDashboard({ navigation }: any) {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [revenue, setRevenue] = useState<any>(null);
  const [transactions, setTransactions] = useState<any>(null);
  const [settlements, setSettlements] = useState<any>(null);
  const [refunds, setRefunds] = useState<any>(null);
  const [dailyRevenue, setDailyRevenue] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    try {
      const [revRes, txRes, settRes, refRes, dailyRes] = await Promise.all([
        settlementApi.getRevenue(),
        settlementApi.getTransactions(),
        settlementApi.getSettlements(),
        settlementApi.getRefunds(),
        settlementApi.getDailyRevenue(),
      ]);
      setRevenue(revRes.data);
      setTransactions(txRes.data);
      setSettlements(settRes.data);
      setRefunds(refRes.data);
      setDailyRevenue(dailyRes.data);
    } catch (error) {
      console.error('Failed to load settlement data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#10B981';
      case 'pending': return '#F59E0B';
      case 'processing': return '#3B82F6';
      case 'failed': return '#EF4444';
      default: return '#6B7280';
    }
  };

  const renderOverviewTab = () => (
    <ScrollView style={styles.tabContent}>
      {/* Wallet Summary */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>💰 Vendor Wallet</Text>
        <View style={styles.walletBalance}>
          <Text style={styles.balanceAmount}>₹{revenue?.wallet?.current_balance || 0}</Text>
          <Text style={styles.balanceLabel}>Current Balance</Text>
        </View>
        <View style={styles.walletDetails}>
          <View style={styles.walletRow}>
            <Text style={styles.walletLabel}>Total Earned</Text>
            <Text style={styles.walletValue}>₹{revenue?.wallet?.total_earned || 0}</Text>
          </View>
          <View style={styles.walletRow}>
            <Text style={styles.walletLabel}>Pending Settlement</Text>
            <Text style={[styles.walletValue, { color: '#F59E0B' }]}>₹{revenue?.wallet?.total_pending || 0}</Text>
          </View>
          <View style={styles.walletRow}>
            <Text style={styles.walletLabel}>Settled</Text>
            <Text style={[styles.walletValue, { color: '#10B981' }]}>₹{revenue?.wallet?.total_settled || 0}</Text>
          </View>
          <View style={styles.walletRow}>
            <Text style={styles.walletLabel}>Total Refunded</Text>
            <Text style={[styles.walletValue, { color: '#EF4444' }]}>₹{revenue?.wallet?.total_refunded || 0}</Text>
          </View>
        </View>
      </View>

      {/* Today's Revenue */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📅 Today's Revenue</Text>
        <View style={styles.todayGrid}>
          <View style={styles.todayCard}>
            <Text style={styles.todayValue}>₹{revenue?.today?.online_payments || 0}</Text>
            <Text style={styles.todayLabel}>Online</Text>
          </View>
          <View style={styles.todayCard}>
            <Text style={styles.todayValue}>₹{revenue?.today?.cash_orders || 0}</Text>
            <Text style={styles.todayLabel}>Cash</Text>
          </View>
          <View style={styles.todayCard}>
            <Text style={[styles.todayValue, { color: '#EF4444' }]}>₹{revenue?.today?.refunds || 0}</Text>
            <Text style={styles.todayLabel}>Refunds</Text>
          </View>
          <View style={styles.todayCard}>
            <Text style={[styles.todayValue, { color: '#10B981' }]}>₹{revenue?.today?.net_revenue || 0}</Text>
            <Text style={styles.todayLabel}>Net</Text>
          </View>
        </View>
      </View>

      {/* Daily Revenue Chart */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📊 Daily Revenue (Last 7 Days)</Text>
        {dailyRevenue?.daily_revenue?.map((day: any, index: number) => (
          <View key={index} style={styles.dailyRow}>
            <Text style={styles.dailyDate}>{day.day_name?.slice(0, 3)}</Text>
            <View style={styles.dailyBars}>
              <View style={[styles.dailyBar, { width: `${Math.min(100, day.online * 2)}%`, backgroundColor: '#3B82F6' }]}>
                <Text style={styles.dailyBarText}>₹{day.online}</Text>
              </View>
            </View>
            <Text style={styles.dailyNet}>₹{day.net}</Text>
          </View>
        ))}
      </View>

      {/* Pending Settlement */}
      {settlements?.pending_settlement && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>⏳ Pending Settlement</Text>
          <View style={styles.pendingRow}>
            <Text style={styles.pendingLabel}>Online Payments</Text>
            <Text style={styles.pendingValue}>₹{settlements.pending_settlement.online_payments}</Text>
          </View>
          <View style={styles.pendingRow}>
            <Text style={styles.pendingLabel}>Cash Orders</Text>
            <Text style={styles.pendingValue}>₹{settlements.pending_settlement.cash_orders}</Text>
          </View>
          <View style={styles.pendingRow}>
            <Text style={styles.pendingLabel}>Refunds</Text>
            <Text style={[styles.pendingValue, { color: '#EF4444' }]}>-₹{settlements.pending_settlement.refunds}</Text>
          </View>
          <View style={[styles.pendingRow, { borderTopWidth: 1, borderTopColor: '#E5E7EB', paddingTop: 8 }]}>
            <Text style={[styles.pendingLabel, { fontWeight: 'bold' }]}>Net Amount</Text>
            <Text style={[styles.pendingValue, { fontWeight: 'bold', color: '#10B981' }]}>₹{settlements.pending_settlement.net_amount}</Text>
          </View>
        </View>
      )}
    </ScrollView>
  );

  const renderTransactionsTab = () => (
    <ScrollView style={styles.tabContent}>
      {/* Summary */}
      {transactions?.summary && (
        <View style={styles.summaryRow}>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryValue}>₹{transactions.summary.total_online}</Text>
            <Text style={styles.summaryLabel}>Online</Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryValue}>₹{transactions.summary.total_cash}</Text>
            <Text style={styles.summaryLabel}>Cash</Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={[styles.summaryValue, { color: '#EF4444' }]}>₹{transactions.summary.total_refunds}</Text>
            <Text style={styles.summaryLabel}>Refunds</Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryValue}>₹{transactions.summary.net_revenue}</Text>
            <Text style={styles.summaryLabel}>Net</Text>
          </View>
        </View>
      )}

      {/* Transaction List */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📋 Recent Transactions</Text>
        {transactions?.transactions?.map((tx: any, index: number) => (
          <View key={index} style={styles.txRow}>
            <View style={styles.txIcon}>
              <Text style={styles.txIconText}>
                {tx.type === 'online_payment' ? '💳' : tx.type === 'cash_order' ? '💵' : '↩️'}
              </Text>
            </View>
            <View style={styles.txInfo}>
              <Text style={styles.txDescription}>{tx.description}</Text>
              <Text style={styles.txDate}>{new Date(tx.created_at).toLocaleDateString()}</Text>
            </View>
            <View style={styles.txAmount}>
              <Text style={[styles.txAmountText, { color: tx.type === 'refund' ? '#EF4444' : '#10B981' }]}>
                {tx.type === 'refund' ? '-' : '+'}₹{tx.amount}
              </Text>
              {tx.fee > 0 && <Text style={styles.txFee}>Fee: ₹{tx.fee}</Text>}
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  );

  const renderSettlementsTab = () => (
    <ScrollView style={styles.tabContent}>
      {/* Wallet Status */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🏦 Settlement Status</Text>
        <View style={styles.settlementStatusRow}>
          <View style={styles.settlementStat}>
            <Text style={styles.settlementStatValue}>₹{settlements?.wallet?.balance || 0}</Text>
            <Text style={styles.settlementStatLabel}>Balance</Text>
          </View>
          <View style={styles.settlementStat}>
            <Text style={[styles.settlementStatValue, { color: '#F59E0B' }]}>₹{settlements?.wallet?.pending || 0}</Text>
            <Text style={styles.settlementStatLabel}>Pending</Text>
          </View>
          <View style={styles.settlementStat}>
            <Text style={[styles.settlementStatValue, { color: '#10B981' }]}>₹{settlements?.wallet?.settled || 0}</Text>
            <Text style={styles.settlementStatLabel}>Settled</Text>
          </View>
        </View>
      </View>

      {/* Settlement History */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📜 Settlement History</Text>
        {settlements?.settlements?.map((settlement: any, index: number) => (
          <View key={index} style={styles.settlementRow}>
            <View style={styles.settlementHeader}>
              <Text style={styles.settlementPeriod}>{settlement.period}</Text>
              <View style={[styles.settlementStatusBadge, { backgroundColor: getStatusColor(settlement.status) }]}>
                <Text style={styles.settlementStatusText}>{settlement.status}</Text>
              </View>
            </View>
            <View style={styles.settlementDetails}>
              <Text style={styles.settlementDetail}>Orders: {settlement.order_count}</Text>
              <Text style={styles.settlementDetail}>Online: ₹{settlement.online_payments}</Text>
              <Text style={styles.settlementDetail}>Cash: ₹{settlement.cash_orders}</Text>
            </View>
            <View style={styles.settlementTotal}>
              <Text style={styles.settlementTotalLabel}>Net Amount</Text>
              <Text style={styles.settlementTotalValue}>₹{settlement.net_amount}</Text>
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  );

  const renderRefundsTab = () => (
    <ScrollView style={styles.tabContent}>
      {/* Refund Summary */}
      <View style={styles.summaryRow}>
        <View style={styles.summaryCard}>
          <Text style={[styles.summaryValue, { color: '#EF4444' }]}>{refunds?.total_refunds || 0}</Text>
          <Text style={styles.summaryLabel}>Total Refunds</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={[styles.summaryValue, { color: '#EF4444' }]}>₹{refunds?.total_refunded_amount || 0}</Text>
          <Text style={styles.summaryLabel}>Amount Refunded</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={[styles.summaryValue, { color: refunds?.refund_rate > 5 ? '#EF4444' : '#10B981' }]}>
            {refunds?.refund_rate || 0}%
          </Text>
          <Text style={styles.summaryLabel}>Refund Rate</Text>
        </View>
      </View>

      {/* Monthly Refund Trend */}
      {refunds?.monthly_refunds?.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>📈 Monthly Refund Trend</Text>
          {refunds.monthly_refunds.map((month: any, index: number) => (
            <View key={index} style={styles.monthlyRefundRow}>
              <Text style={styles.monthlyRefundLabel}>{month.label}</Text>
              <View style={styles.monthlyRefundBar}>
                <View style={[styles.refundBar, { width: `${Math.min(100, month.refund_amount * 2)}%`, backgroundColor: '#EF4444' }]}>
                  <Text style={styles.refundBarText}>₹{month.refund_amount}</Text>
                </View>
              </View>
              <Text style={styles.monthlyRefundCount}>{month.refund_count}x</Text>
            </View>
          ))}
        </View>
      )}

      {/* Refund List */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>↩️ Recent Refunds</Text>
        {refunds?.refunds?.map((refund: any, index: number) => (
          <View key={index} style={styles.refundRow}>
            <View style={styles.refundInfo}>
              <Text style={styles.refundOrder}>Order #{refund.order_id}</Text>
              <Text style={styles.refundDate}>{new Date(refund.created_at).toLocaleDateString()}</Text>
              {refund.razorpay_refund_id && (
                <Text style={styles.refundId}>Refund ID: {refund.razorpay_refund_id}</Text>
              )}
            </View>
            <View style={styles.refundAmount}>
              <Text style={styles.refundAmountText}>-₹{refund.amount}</Text>
              <View style={[styles.refundStatus, { backgroundColor: refund.status === 'processed' ? '#10B981' : '#F59E0B' }]}>
                <Text style={styles.refundStatusText}>{refund.status}</Text>
              </View>
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading settlement data...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>💰 Settlements</Text>
        <Text style={styles.headerSubtitle}>Financial overview for {user?.vendor_name}</Text>
      </View>

      <View style={styles.tabContainer}>
        <TouchableOpacity style={[styles.tab, activeTab === 'overview' && styles.activeTab]} onPress={() => setActiveTab('overview')}>
          <Text style={[styles.tabText, activeTab === 'overview' && styles.activeTabText]}>📊 Overview</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'transactions' && styles.activeTab]} onPress={() => setActiveTab('transactions')}>
          <Text style={[styles.tabText, activeTab === 'transactions' && styles.activeTabText]}>💳 Transactions</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'settlements' && styles.activeTab]} onPress={() => setActiveTab('settlements')}>
          <Text style={[styles.tabText, activeTab === 'settlements' && styles.activeTabText]}>🏦 Settlements</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tab, activeTab === 'refunds' && styles.activeTab]} onPress={() => setActiveTab('refunds')}>
          <Text style={[styles.tabText, activeTab === 'refunds' && styles.activeTabText]}>↩️ Refunds</Text>
        </TouchableOpacity>
      </View>

      {activeTab === 'overview' && renderOverviewTab()}
      {activeTab === 'transactions' && renderTransactionsTab()}
      {activeTab === 'settlements' && renderSettlementsTab()}
      {activeTab === 'refunds' && renderRefundsTab()}
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
  tabContainer: { flexDirection: 'row', paddingHorizontal: 12, paddingVertical: 10, gap: 3, backgroundColor: 'white', borderBottomWidth: 1, borderBottomColor: '#E5E7EB' },
  tab: { flex: 1, paddingVertical: 8, borderRadius: 8, backgroundColor: '#F3F5F9', alignItems: 'center' },
  activeTab: { backgroundColor: '#10B981' },
  tabText: { fontSize: 11, fontWeight: '600', color: '#6B7280' },
  activeTabText: { color: 'white' },
  tabContent: { padding: 16 },
  card: { backgroundColor: 'white', borderRadius: 12, padding: 16, marginBottom: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  cardTitle: { fontSize: 18, fontWeight: 'bold', color: '#111827', marginBottom: 12 },
  walletBalance: { alignItems: 'center', paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: '#E5E7EB', marginBottom: 12 },
  balanceAmount: { fontSize: 36, fontWeight: 'bold', color: '#10B981' },
  balanceLabel: { fontSize: 14, color: '#6B7280', marginTop: 4 },
  walletDetails: { gap: 8 },
  walletRow: { flexDirection: 'row', justifyContent: 'space-between' },
  walletLabel: { fontSize: 14, color: '#6B7280' },
  walletValue: { fontSize: 14, fontWeight: '600', color: '#111827' },
  todayGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  todayCard: { flex: 1, minWidth: '45%', backgroundColor: '#F3F5F9', borderRadius: 8, padding: 12, alignItems: 'center' },
  todayValue: { fontSize: 18, fontWeight: 'bold', color: '#111827' },
  todayLabel: { fontSize: 11, color: '#6B7280', marginTop: 4 },
  dailyRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  dailyDate: { fontSize: 12, fontWeight: '600', color: '#374151', width: 40 },
  dailyBars: { flex: 1, marginHorizontal: 8 },
  dailyBar: { height: 20, borderRadius: 4, justifyContent: 'center', paddingHorizontal: 6, minWidth: 30 },
  dailyBarText: { color: 'white', fontSize: 10, fontWeight: '600' },
  dailyNet: { fontSize: 12, fontWeight: '600', color: '#10B981', width: 60, textAlign: 'right' },
  pendingRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 },
  pendingLabel: { fontSize: 14, color: '#6B7280' },
  pendingValue: { fontSize: 14, fontWeight: '600', color: '#111827' },
  summaryRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  summaryCard: { flex: 1, backgroundColor: 'white', borderRadius: 12, padding: 12, alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  summaryValue: { fontSize: 16, fontWeight: 'bold', color: '#10B981' },
  summaryLabel: { fontSize: 10, color: '#6B7280', marginTop: 4 },
  txRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  txIcon: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#F3F5F9', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  txIconText: { fontSize: 18 },
  txInfo: { flex: 1 },
  txDescription: { fontSize: 14, fontWeight: '500', color: '#111827' },
  txDate: { fontSize: 12, color: '#6B7280', marginTop: 2 },
  txAmount: { alignItems: 'flex-end' },
  txAmountText: { fontSize: 14, fontWeight: 'bold' },
  txFee: { fontSize: 11, color: '#6B7280' },
  settlementStatusRow: { flexDirection: 'row', gap: 8 },
  settlementStat: { flex: 1, alignItems: 'center' },
  settlementStatValue: { fontSize: 20, fontWeight: 'bold', color: '#111827' },
  settlementStatLabel: { fontSize: 11, color: '#6B7280', marginTop: 4 },
  settlementRow: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  settlementHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  settlementPeriod: { fontSize: 14, fontWeight: '600', color: '#111827' },
  settlementStatusBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  settlementStatusText: { color: 'white', fontSize: 10, fontWeight: '600' },
  settlementDetails: { marginBottom: 8, gap: 2 },
  settlementDetail: { fontSize: 12, color: '#6B7280' },
  settlementTotal: { flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: '#E5E7EB', paddingTop: 8 },
  settlementTotalLabel: { fontSize: 14, fontWeight: '600', color: '#374151' },
  settlementTotalValue: { fontSize: 16, fontWeight: 'bold', color: '#10B981' },
  monthlyRefundRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  monthlyRefundLabel: { fontSize: 12, fontWeight: '600', color: '#374151', width: 70 },
  monthlyRefundBar: { flex: 1, marginHorizontal: 8 },
  refundBar: { height: 20, borderRadius: 4, justifyContent: 'center', paddingHorizontal: 6, minWidth: 30 },
  refundBarText: { color: 'white', fontSize: 10, fontWeight: '600' },
  monthlyRefundCount: { fontSize: 12, color: '#6B7280', width: 30, textAlign: 'right' },
  refundRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  refundInfo: { flex: 1 },
  refundOrder: { fontSize: 14, fontWeight: '600', color: '#111827' },
  refundDate: { fontSize: 12, color: '#6B7280', marginTop: 2 },
  refundId: { fontSize: 11, color: '#9CA3AF', marginTop: 2 },
  refundAmount: { alignItems: 'flex-end' },
  refundAmountText: { fontSize: 16, fontWeight: 'bold', color: '#EF4444' },
  refundStatus: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8, marginTop: 4 },
  refundStatusText: { color: 'white', fontSize: 10, fontWeight: '600' },
});