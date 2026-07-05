// ─── Restock Suggestions ─────────────────────────────────────────
// Calls existing /restock-suggestions endpoint to show AI-powered
// auto-restock recommendations with priority, quantity, and reasoning.

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
import GlassCard from '../../design-system/components/GlassCard';
import StatCard from '../../design-system/components/StatCard';
import Badge from '../../design-system/components/Badge';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';
import {useTheme} from '../../context/ThemeContext';

interface RestockSuggestion {
  item_name: string;
  current_stock: number;
  suggested_quantity: number;
  priority: 'critical' | 'high' | 'medium' | 'low';
  reason: string;
  daily_demand?: number;
  days_until_out?: number;
  restock_by?: string;
}

export default function RestockSuggestionsScreen() {
  const {colors: themeColors} = useTheme();
  const [suggestions, setSuggestions] = useState<RestockSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {toValue: 1, duration: 400, useNativeDriver: true}).start();
    loadSuggestions();
  }, []);

  const loadSuggestions = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      setError(null);
      const res = await vendorApi.getRestockSuggestions();
      const s = (res.data as any)?.suggestions || [];
      setSuggestions(s);
    } catch (err: any) {
      setError(err?.message || 'Failed to load restock suggestions');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadSuggestions(true);
  };

  const critical = suggestions.filter(s => s.priority === 'critical');
  const high = suggestions.filter(s => s.priority === 'high');
  const medium = suggestions.filter(s => s.priority === 'medium');
  const low = suggestions.filter(s => s.priority === 'low');

  const getPriorityColor = (p: string) => {
    switch (p) {
      case 'critical': return themeColors.error;
      case 'high': return themeColors.warning;
      case 'medium': return themeColors.info;
      default: return themeColors.success;
    }
  };

  const getPriorityVariant = (p: string): 'error' | 'warning' | 'info' | 'success' => {
    switch (p) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      default: return 'success';
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, {backgroundColor: themeColors.bg}, styles.centered]}>
        <ActivityIndicator size="large" color={themeColors.primary} />
        <Text style={[styles.loadingText, {color: themeColors.textMuted}]}>Loading restock suggestions...</Text>
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
        <Text style={[styles.headerTitle, {color: themeColors.textInverse}]}>Auto-Restock</Text>
        <Text style={[styles.headerSubtitle, {color: 'rgba(255,255,255,0.7)'}]}>
          {suggestions.length} items need attention
        </Text>
      </View>

      {error && (
        <GlassCard padding={14} borderRadius={16} style={{marginHorizontal: spacing.lg, marginTop: spacing.md, backgroundColor: themeColors.errorPale}}>
          <Text style={{color: themeColors.error, fontSize: 14}}>{error}</Text>
          <TouchableOpacity onPress={() => loadSuggestions()}>
            <Text style={{color: themeColors.error, fontWeight: '700', marginTop: 8}}>Retry</Text>
          </TouchableOpacity>
        </GlassCard>
      )}

      <Animated.View style={{opacity: fadeAnim, padding: spacing.lg}}>
        {/* Summary Stats */}
        <View style={styles.statsRow}>
          <StatCard value={critical.length} label="Critical" icon="🔴" color={themeColors.error} size="sm" style={{flex: 1}} />
          <StatCard value={high.length} label="High" icon="🟡" color={themeColors.warning} size="sm" style={{flex: 1}} />
          <StatCard value={medium.length} label="Medium" icon="🔵" color={themeColors.info} size="sm" style={{flex: 1}} />
          <StatCard value={low.length} label="Low" icon="🟢" color={themeColors.success} size="sm" style={{flex: 1}} />
        </View>

        {/* Priority Sections */}
        {critical.length > 0 && (
          <View style={{marginBottom: spacing.md}}>
            <Text style={[styles.sectionLabel, {color: themeColors.error}]}>🔴 Critical — Restock Immediately</Text>
            {critical.map((s, i) => <SuggestionCard key={`c-${i}`} suggestion={s} themeColors={themeColors} />)}
          </View>
        )}

        {high.length > 0 && (
          <View style={{marginBottom: spacing.md}}>
            <Text style={[styles.sectionLabel, {color: themeColors.warning}]}>🟡 High Priority</Text>
            {high.map((s, i) => <SuggestionCard key={`h-${i}`} suggestion={s} themeColors={themeColors} />)}
          </View>
        )}

        {medium.length > 0 && (
          <View style={{marginBottom: spacing.md}}>
            <Text style={[styles.sectionLabel, {color: themeColors.info}]}>🔵 Medium Priority</Text>
            {medium.map((s, i) => <SuggestionCard key={`m-${i}`} suggestion={s} themeColors={themeColors} />)}
          </View>
        )}

        {low.length > 0 && (
          <View style={{marginBottom: spacing.md}}>
            <Text style={[styles.sectionLabel, {color: themeColors.success}]}>🟢 Low Priority</Text>
            {low.map((s, i) => <SuggestionCard key={`l-${i}`} suggestion={s} themeColors={themeColors} />)}
          </View>
        )}

        {suggestions.length === 0 && !error && (
          <PremiumEmptyState
            icon="✅"
            title="All Stocked Up"
            description="All items are adequately stocked. No restock suggestions at this time."
          />
        )}
        <View style={{height: spacing.huge}} />
      </Animated.View>
    </ScrollView>
  );
}

function SuggestionCard({suggestion, themeColors}: {suggestion: RestockSuggestion; themeColors: any}) {
  const priorityColor = (() => {
    switch (suggestion.priority) {
      case 'critical': return themeColors.error;
      case 'high': return themeColors.warning;
      case 'medium': return themeColors.info;
      default: return themeColors.success;
    }
  })();

  return (
    <GlassCard padding={16} borderRadius={18} style={{marginBottom: spacing.sm}}>
      <View style={suggestionStyles.header}>
        <Text style={[suggestionStyles.name, {color: themeColors.textPrimary}]}>{suggestion.item_name}</Text>
        <Badge label={suggestion.priority} variant={suggestion.priority === 'critical' ? 'error' : suggestion.priority === 'high' ? 'warning' : suggestion.priority === 'medium' ? 'info' : 'success'} size="sm" />
      </View>

      <View style={suggestionStyles.details}>
        <View style={suggestionStyles.detailRow}>
          <Text style={[suggestionStyles.label, {color: themeColors.textMuted}]}>Current Stock</Text>
          <Text style={[suggestionStyles.value, {color: themeColors.textPrimary}]}>{suggestion.current_stock} units</Text>
        </View>
        <View style={suggestionStyles.detailRow}>
          <Text style={[suggestionStyles.label, {color: themeColors.textMuted}]}>Suggested Restock</Text>
          <Text style={[suggestionStyles.value, {color: priorityColor, fontWeight: '700'}]}>{suggestion.suggested_quantity} units</Text>
        </View>
        {suggestion.days_until_out !== undefined && (
          <View style={suggestionStyles.detailRow}>
            <Text style={[suggestionStyles.label, {color: themeColors.textMuted}]}>Days Until Out</Text>
            <Text style={[suggestionStyles.value, {color: (suggestion.days_until_out ?? 99) <= 2 ? themeColors.error : themeColors.textPrimary}]}>
              {suggestion.days_until_out}d
            </Text>
          </View>
        )}
        {suggestion.daily_demand !== undefined && (
          <View style={suggestionStyles.detailRow}>
            <Text style={[suggestionStyles.label, {color: themeColors.textMuted}]}>Daily Demand</Text>
            <Text style={[suggestionStyles.value, {color: themeColors.textPrimary}]}>{suggestion.daily_demand}/day</Text>
          </View>
        )}
        {suggestion.restock_by && (
          <View style={suggestionStyles.detailRow}>
            <Text style={[suggestionStyles.label, {color: themeColors.textMuted}]}>Restock By</Text>
            <Text style={[suggestionStyles.value, {color: themeColors.warning}]}>{suggestion.restock_by}</Text>
          </View>
        )}
      </View>

      <View style={[suggestionStyles.reasonBox, {backgroundColor: priorityColor + '12'}]}>
        <Text style={[suggestionStyles.reasonIcon]}>💡</Text>
        <Text style={[suggestionStyles.reasonText, {color: priorityColor}]}>{suggestion.reason}</Text>
      </View>
    </GlassCard>
  );
}

const suggestionStyles = StyleSheet.create({
  header: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12},
  name: {fontSize: 16, fontWeight: '600', flex: 1},
  details: {gap: 6, marginBottom: 10},
  detailRow: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'},
  label: {fontSize: 13, color: colors.textMuted},
  value: {fontSize: 14, fontWeight: '600'},
  reasonBox: {flexDirection: 'row', borderRadius: 10, padding: 10, gap: 6, alignItems: 'flex-start'},
  reasonIcon: {fontSize: 14, marginTop: 1},
  reasonText: {flex: 1, fontSize: 13, lineHeight: 18},
});

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.bg},
  centered: {justifyContent: 'center', alignItems: 'center'},
  loadingText: {marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600'},
  header: {
    backgroundColor: colors.primary,
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
  headerSubtitle: {fontSize: 14, marginTop: 4, fontWeight: '500'},
  statsRow: {flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md},
  sectionLabel: {fontSize: 16, fontWeight: '700', marginBottom: spacing.sm},
});
