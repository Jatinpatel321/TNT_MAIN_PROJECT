// ─── Premium Slot Dashboard ──────────────────────────────────────
// Premium slot management with design system (#635BFF, GlassCard)

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
  Animated,
} from 'react-native';
import { slotApi } from '../../services/slotApi';
import { colors, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import StatCard from '../../design-system/components/StatCard';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';
import Button from '../../design-system/components/Button';

export default function SlotDashboardScreen({ navigation }: any) {
  const [slots, setSlots] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    fetchSlots();
  }, []);

  const fetchSlots = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      const [slotsRes, analyticsRes] = await Promise.all([
        slotApi.getSlots(),
        slotApi.getAnalytics(),
      ]);
      setSlots(slotsRes.data || []);
      setAnalytics(analyticsRes.data);
    } catch (err: any) {
      console.error('Slots fetch error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => { setRefreshing(true); fetchSlots(true); }, []);

  const handleLockSlot = async (id: number) => {
    try { await slotApi.lockSlot(id); fetchSlots(); } catch (err: any) { Alert.alert('Error', err.message); }
  };

  const handleUnlockSlot = async (id: number) => {
    try { await slotApi.unlockSlot(id); fetchSlots(); } catch (err: any) { Alert.alert('Error', err.message); }
  };

  const handleDeleteSlot = (id: number) => {
    Alert.alert('Delete Slot', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => { try { await slotApi.deleteSlot(id); fetchSlots(); } catch (err: any) { Alert.alert('Error', err.message); } } },
    ]);
  };

  const formatTime = (t: string) => {
    try { return new Date(t).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }); } catch { return t; }
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading slots...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Slot Management</Text>
        <Text style={styles.headerSubtitle}>{slots.length} active slots</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        {/* Analytics */}
        {analytics && (
          <View style={styles.statsRow}>
            <StatCard value={analytics.total_slots || 0} label="Total" icon="📋" color={colors.primary} size="sm" style={{ flex: 1 }} />
            <StatCard value={analytics.active_slots || 0} label="Active" icon="✅" color={colors.success} size="sm" style={{ flex: 1 }} />
            <StatCard value={analytics.blocked_slots || 0} label="Blocked" icon="🔒" color={colors.error} size="sm" style={{ flex: 1 }} />
            <StatCard value={analytics.utilization_rate ? Math.round(analytics.utilization_rate * 100) : 0} label="Util. %" icon="📊" color={colors.secondary} size="sm" style={{ flex: 1 }} />
          </View>
        )}

        {/* Actions */}
        <View style={styles.actionsRow}>
          <Button title="+ Create Slots" onPress={() => navigation.navigate('SlotConfiguration')} variant="primary" size="md" style={{ flex: 1 }} />
          <Button title="⚙️ Capacity" onPress={() => navigation.navigate('CapacitySettings')} variant="secondary" size="md" style={{ flex: 1 }} />
        </View>

        {/* Slot List */}
        {slots.length === 0 ? (
          <PremiumEmptyState icon="📋" title="No slots" description="Create your first time slot" onAction={() => navigation.navigate('SlotConfiguration')} actionLabel="Create Slot" />
        ) : (
          slots.map(slot => (
            <GlassCard key={slot.id} padding={16} borderRadius={18} style={{ marginHorizontal: spacing.lg, marginBottom: spacing.sm }}>
              <View style={styles.slotHeader}>
                <View style={styles.timeRow}>
                  <Text style={styles.timeText}>{formatTime(slot.start_time)}</Text>
                  <Text style={styles.timeArrow}>→</Text>
                  <Text style={styles.timeText}>{formatTime(slot.end_time)}</Text>
                </View>
                <StatusPill label={slot.status || 'available'} variant={slot.status === 'available' ? 'success' : slot.status === 'blocked' ? 'error' : 'warning'} size="sm" />
              </View>
              <View style={styles.slotDetails}>
                <SlotDetail label="Capacity" value={`${slot.current_orders || 0}/${slot.max_orders || 0}`} />
                <SlotDetail label="Available" value={slot.available_capacity ?? 0} color={colors.success} />
                <SlotDetail label="Load" value={slot.load_label || 'N/A'} color={slot.load_label === 'high' ? colors.error : slot.load_label === 'medium' ? colors.warning : colors.success} />
                <SlotDetail label="Queue" value={slot.queue_size || 0} />
                <SlotDetail label="Wait" value={`${slot.estimated_wait || 0}min`} />
              </View>
              {slot.faculty_priority && (
                <View style={styles.facultyBadge}><Text style={styles.facultyText}>👨‍🏫 Faculty Priority</Text></View>
              )}
              <View style={styles.slotActions}>
                {slot.is_locked ? (
                  <Button title="🔓 Unlock" onPress={() => handleUnlockSlot(slot.id)} variant="success" size="sm" style={{ flex: 1 }} />
                ) : (
                  <Button title="🔒 Lock" onPress={() => handleLockSlot(slot.id)} variant="warning" size="sm" style={{ flex: 1 }} />
                )}
                <Button title="🗑️ Delete" onPress={() => handleDeleteSlot(slot.id)} variant="danger" size="sm" style={{ flex: 1 }} />
              </View>
            </GlassCard>
          ))
        )}
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

function SlotDetail({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <View style={detailStyles.row}>
      <Text style={detailStyles.label}>{label}</Text>
      <Text style={[detailStyles.value, color ? { color } : undefined]}>{value}</Text>
    </View>
  );
}

const detailStyles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  label: { fontSize: 13, color: colors.textMuted },
  value: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },
  header: {
    backgroundColor: colors.primary, paddingTop: spacing.huge + 20, paddingBottom: spacing.xxl, paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28, borderBottomRightRadius: 28, overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  statsRow: { flexDirection: 'row', paddingHorizontal: spacing.lg, marginTop: -16, marginBottom: spacing.md, gap: spacing.sm },
  actionsRow: { flexDirection: 'row', gap: spacing.sm, paddingHorizontal: spacing.lg, marginBottom: spacing.md },
  slotHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  timeRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  timeText: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  timeArrow: { fontSize: 14, color: colors.textMuted },
  slotDetails: { marginBottom: 12 },
  facultyBadge: { backgroundColor: colors.secondaryPale, padding: 8, borderRadius: 10, marginBottom: 10 },
  facultyText: { fontSize: 12, color: colors.secondary, fontWeight: '600' },
  slotActions: { flexDirection: 'row', gap: 8 },
});
