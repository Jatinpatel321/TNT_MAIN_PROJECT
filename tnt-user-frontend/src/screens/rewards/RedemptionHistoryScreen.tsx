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
import { getTransactionHistory, getRedemptionHistory } from '../../services/rewardsService';
import type { RewardTransaction, RewardRedemption, RewardTypeKey, RedemptionTypeKey } from '../../types/models';

type Props = NativeStackScreenProps<RootStackParamList, 'RedemptionHistory'>;

const REWARD_ICONS: Record<RewardTypeKey, { icon: string; color: string }> = {
  order_completion: { icon: 'check-circle', color: '#059669' },
  first_order: { icon: 'party-popper', color: '#7C3AED' },
  referral: { icon: 'account-plus', color: '#2563EB' },
  loyalty_milestone: { icon: 'trophy', color: '#D97706' },
  off_peak_bonus: { icon: 'clock-outline', color: '#0891B2' },
  voucher_redemption: { icon: 'ticket-percent', color: '#DC2626' },
};

const REDEMPTION_ICONS: Record<RedemptionTypeKey, { icon: string; color: string }> = {
  discount_percentage: { icon: 'percent', color: '#2563EB' },
  discount_fixed: { icon: 'cash-minus', color: '#D97706' },
  free_item: { icon: 'gift', color: '#059669' },
};

type TabKey = 'all' | 'earned' | 'redeemed';

export function RedemptionHistoryScreen({}: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>('all');
  const [transactions, setTransactions] = useState<RewardTransaction[]>([]);
  const [redemptions, setRedemptions] = useState<RewardRedemption[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const [t, r] = await Promise.all([
        getTransactionHistory(100, 0),
        getRedemptionHistory(100, 0),
      ]);
      setTransactions(t);
      setRedemptions(r);
    } catch {
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
          <ActivityIndicator size="large" color="#3B82F6" />
        </View>
      </Screen>
    );
  }

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'earned', label: 'Earned' },
    { key: 'redeemed', label: 'Redeemed' },
  ];

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Text style={styles.title}>Reward History</Text>
        </View>

        <View style={styles.tabRow}>
          {tabs.map((tab) => (
            <Pressable
              key={tab.key}
              onPress={() => setActiveTab(tab.key)}
              style={[styles.tab, activeTab === tab.key && styles.tabActive]}
            >
              <Text
                style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]}
              >
                {tab.label}
              </Text>
            </Pressable>
          ))}
        </View>

        {/* Earned items */}
        {(activeTab === 'all' || activeTab === 'earned') &&
          transactions.map((t) => {
            const config = REWARD_ICONS[t.reward_type] ?? REWARD_ICONS.order_completion;
            return (
              <View key={`t-${t.id}`} style={styles.item}>
                <View style={[styles.itemIcon, { backgroundColor: config.color + '15' }]}>
                  <MaterialCommunityIcons
                    name={config.icon as any}
                    size={18}
                    color={config.color}
                  />
                </View>
                <View style={styles.itemContent}>
                  <Text style={styles.itemDesc}>{t.description}</Text>
                  <Text style={styles.itemDate}>
                    {new Date(t.created_at).toLocaleDateString()}
                  </Text>
                </View>
                <Text style={styles.itemPointsEarned}>+{Math.floor(t.points)}</Text>
              </View>
            );
          })}

        {/* Redeemed items */}
        {(activeTab === 'all' || activeTab === 'redeemed') &&
          redemptions.map((r) => {
            const config = REDEMPTION_ICONS[r.redemption_type] ?? REDEMPTION_ICONS.discount_fixed;
            return (
              <View key={`r-${r.id}`} style={styles.item}>
                <View style={[styles.itemIcon, { backgroundColor: config.color + '15' }]}>
                  <MaterialCommunityIcons
                    name={config.icon as any}
                    size={18}
                    color={config.color}
                  />
                </View>
                <View style={styles.itemContent}>
                  <Text style={styles.itemDesc}>{r.description}</Text>
                  <Text style={styles.itemDate}>
                    {new Date(r.created_at).toLocaleDateString()}
                  </Text>
                </View>
                <Text style={styles.itemPointsRedeemed}>-{Math.floor(r.points_used)}</Text>
              </View>
            );
          })}

        {transactions.length === 0 && redemptions.length === 0 && (
          <View style={styles.emptyState}>
            <MaterialCommunityIcons name="history" size={40} color="#D1D5DB" />
            <Text style={styles.emptyText}>No reward history yet.</Text>
          </View>
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: 32,
    gap: 12,
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
    color: '#111827',
  },
  tabRow: {
    flexDirection: 'row',
    gap: 8,
  },
  tab: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 12,
    backgroundColor: '#F3F4F6',
  },
  tabActive: {
    backgroundColor: '#3B82F6',
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
  },
  tabTextActive: {
    color: '#FFFFFF',
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 12,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 4,
    elevation: 2,
  },
  itemIcon: {
    width: 34,
    height: 34,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemContent: {
    flex: 1,
    gap: 2,
  },
  itemDesc: {
    fontSize: 13,
    fontWeight: '600',
    color: '#374151',
  },
  itemDate: {
    fontSize: 11,
    color: '#9CA3AF',
  },
  itemPointsEarned: {
    fontSize: 14,
    fontWeight: '800',
    color: '#059669',
  },
  itemPointsRedeemed: {
    fontSize: 14,
    fontWeight: '800',
    color: '#DC2626',
  },
  emptyState: {
    backgroundColor: '#F9FAFB',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    gap: 8,
  },
  emptyText: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
  },
});
