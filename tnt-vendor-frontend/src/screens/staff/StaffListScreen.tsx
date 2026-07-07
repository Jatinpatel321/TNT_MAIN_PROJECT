// ─── Premium Staff Management ─────────────────────────────────
// Premium team management with design system

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
import { staffApi, type StaffMember } from '../../services/staffApi';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import StatCard from '../../design-system/components/StatCard';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';

export default function StaffListScreen({ navigation }: any) {
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    fetchStaff();
  }, []);

  const fetchStaff = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      const response = await staffApi.getStaff();
      // Backend returns a list directly (not wrapped in { staff: [] })
      const data = response.data;
      setStaff(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.error('Staff fetch error:', err?.response?.data || err?.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchStaff(true);
  }, []);

  const handleDeleteStaff = (member: StaffMember) => {
    Alert.alert('Delete Staff', `Remove ${member.name}?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await staffApi.deleteStaff(member.id);
            fetchStaff();
          } catch (err: any) {
            Alert.alert('Error', err?.response?.data?.detail || err.message);
          }
        },
      },
    ]);
  };

  const roleConfig: Record<string, { label: string; color: string; icon: string }> = {
    manager: { label: 'Manager', color: colors.info, icon: '👔' },
    staff: { label: 'Staff', color: colors.success, icon: '👤' },
  };

  /** Returns count of granted permissions (dict keys) */
  const permissionCount = (perms: StaffMember['permissions']): number => {
    if (!perms) return 0;
    return Object.keys(perms).length;
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading staff...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
    >
      <View style={styles.header}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Staff Management</Text>
        <Text style={styles.headerSubtitle}>{staff.length} team member{staff.length !== 1 ? 's' : ''}</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        <View style={styles.statsRow}>
          <StatCard value={staff.filter(s => s.is_active).length} label="Active" icon="✅" color={colors.success} size="sm" style={{ flex: 1 }} />
          <StatCard value={staff.filter(s => s.role === 'manager').length} label="Managers" icon="👔" color={colors.info} size="sm" style={{ flex: 1 }} />
          <StatCard value={staff.filter(s => s.role === 'staff').length} label="Staff" icon="👤" color={colors.primary} size="sm" style={{ flex: 1 }} />
        </View>

        <View style={styles.section}>
          <TouchableOpacity style={styles.addBtn} onPress={() => navigation.navigate('AddStaff')}>
            <Text style={styles.addBtnText}>+ Add Staff Member</Text>
          </TouchableOpacity>
        </View>

        {staff.length === 0 ? (
          <PremiumEmptyState
            icon="👥"
            title="No team members"
            description="Add your first staff member to get started"
            onAction={() => navigation.navigate('AddStaff')}
            actionLabel="Add Staff"
          />
        ) : (
          <View style={styles.section}>
            {staff.map(member => {
              const role = roleConfig[member.role] || roleConfig.staff;
              return (
                <GlassCard key={member.id} padding={16} borderRadius={18} style={{ marginBottom: spacing.sm }}>
                  <View style={styles.memberHeader}>
                    <View style={[styles.avatarCircle, { backgroundColor: role.color + '15' }]}>
                      <Text style={styles.avatarEmoji}>{role.icon}</Text>
                    </View>
                    <View style={styles.memberInfo}>
                      <Text style={styles.memberName}>{member.name}</Text>
                      <Text style={styles.memberPhone}>{member.phone}</Text>
                    </View>
                    <StatusPill label={role.label} variant="primary" size="sm" />
                  </View>
                  <View style={styles.memberMeta}>
                    <StatusPill label={member.is_active ? 'Active' : 'Inactive'} variant={member.is_active ? 'success' : 'neutral'} size="sm" />
                    <Text style={styles.permissionsCount}>{permissionCount(member.permissions)} permissions</Text>
                  </View>
                  <View style={styles.memberActions}>
                    <ActionBtn
                      label="Edit"
                      color={colors.info}
                      onPress={() => navigation.navigate('EditStaff', { staff: member })}
                    />
                    <ActionBtn
                      label="Permissions"
                      color={colors.secondary}
                      onPress={() => navigation.navigate('StaffPermissions', { staff: member })}
                    />
                    <ActionBtn
                      label="Delete"
                      color={colors.error}
                      onPress={() => handleDeleteStaff(member)}
                    />
                  </View>
                </GlassCard>
              );
            })}
          </View>
        )}
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

function ActionBtn({ label, color, onPress }: { label: string; color: string; onPress: () => void }) {
  return (
    <TouchableOpacity style={[actionStyles.btn, { backgroundColor: color + '15' }]} onPress={onPress}>
      <Text style={[actionStyles.text, { color }]}>{label}</Text>
    </TouchableOpacity>
  );
}

const actionStyles = StyleSheet.create({
  btn: { flex: 1, paddingVertical: 8, borderRadius: 10, alignItems: 'center' },
  text: { fontSize: 12, fontWeight: '600' },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.huge + 20,
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
  statsRow: { flexDirection: 'row', paddingHorizontal: spacing.lg, marginTop: -16, marginBottom: spacing.md, gap: spacing.sm },
  section: { paddingHorizontal: spacing.lg, marginBottom: spacing.sm },
  addBtn: { backgroundColor: colors.primary, borderRadius: 16, padding: 16, alignItems: 'center', ...shadows.button },
  addBtnText: { color: colors.textInverse, fontSize: 16, fontWeight: '700' },
  memberHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 10 },
  avatarCircle: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  avatarEmoji: { fontSize: 22 },
  memberInfo: { flex: 1 },
  memberName: { fontSize: 16, fontWeight: '600', color: colors.textPrimary },
  memberPhone: { fontSize: 13, color: colors.textMuted, marginTop: 2 },
  memberMeta: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10 },
  permissionsCount: { fontSize: 12, color: colors.textMuted, fontWeight: '500' },
  memberActions: { flexDirection: 'row', gap: 8 },
});
