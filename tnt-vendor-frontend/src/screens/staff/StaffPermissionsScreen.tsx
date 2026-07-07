// ─── Premium Staff Permissions Screen ────────────────────────────
// Manage staff permissions — uses static permission module list
// (no /permissions endpoint on backend — permissions are a dict on StaffMember)

import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  Animated,
} from 'react-native';
import { staffApi, type StaffMember } from '../../services/staffApi';
import { colors, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Button from '../../design-system/components/Button';

// Static list — same set used in Add/Edit Staff screens
const AVAILABLE_PERMISSIONS = [
  { key: 'orders', label: 'Orders', icon: '📋', description: 'View and manage customer orders' },
  { key: 'menu', label: 'Menu', icon: '🍽️', description: 'Edit menu items and availability' },
  { key: 'inventory', label: 'Inventory', icon: '📦', description: 'Manage stock and inventory' },
  { key: 'analytics', label: 'Analytics', icon: '📊', description: 'View sales and analytics data' },
  { key: 'slots', label: 'Slots', icon: '⏰', description: 'Configure time slots and capacity' },
  { key: 'staff', label: 'Staff', icon: '👥', description: 'Manage team members (manager only)' },
  { key: 'settlements', label: 'Settlements', icon: '💰', description: 'View payout and settlement data' },
  { key: 'promotions', label: 'Promotions', icon: '🎯', description: 'Create and manage promotions' },
];

const ROLE_DEFAULTS: Record<string, string[]> = {
  manager: ['orders', 'menu', 'analytics', 'inventory', 'slots'],
  staff: ['orders', 'menu'],
};

/** Convert permissions dict to a set of enabled keys */
function permDictToSet(perms: StaffMember['permissions']): Set<string> {
  if (!perms) return new Set();
  return new Set(Object.keys(perms).filter(k => perms[k]));
}

export default function StaffPermissionsScreen({ route, navigation }: any) {
  const { staff } = route.params as { staff: StaffMember };
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(permDictToSet(staff.permissions));
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useState(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
  });

  const toggle = (key: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(key)) { next.delete(key); } else { next.add(key); }
      return next;
    });
  };

  const selectAll = () => setSelected(new Set(AVAILABLE_PERMISSIONS.map(p => p.key)));
  const selectNone = () => setSelected(new Set());
  const selectDefaults = () => setSelected(new Set(ROLE_DEFAULTS[staff.role] || []));

  const handleSave = async () => {
    try {
      setLoading(true);
      // Build permissions dict from selected set
      const permissionsDict: Record<string, boolean> = {};
      selected.forEach(key => { permissionsDict[key] = true; });

      await staffApi.updateStaff(staff.id, { permissions: permissionsDict });
      Alert.alert('Success', 'Permissions updated successfully', [
        { text: 'OK', onPress: () => navigation.goBack() },
      ]);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to update permissions';
      Alert.alert('Error', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Permissions</Text>
        <Text style={styles.headerSubtitle}>{staff.name} · {staff.role}</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim, flex: 1 }}>
        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <TouchableOpacity style={styles.quickBtn} onPress={selectAll}>
            <Text style={styles.quickText}>✅ All</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.quickBtn} onPress={selectNone}>
            <Text style={styles.quickText}>❌ None</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.quickBtn} onPress={selectDefaults}>
            <Text style={styles.quickText}>🔄 Default</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.selectedCount}>{selected.size} permissions granted</Text>

        {/* Permission Toggles */}
        {AVAILABLE_PERMISSIONS.map(p => {
          const isSelected = selected.has(p.key);
          return (
            <TouchableOpacity key={p.key} onPress={() => toggle(p.key)} activeOpacity={0.7}>
              <GlassCard
                padding={14}
                borderRadius={16}
                style={{ marginHorizontal: spacing.lg, marginBottom: 6 }}
              >
                <View style={styles.permRow}>
                  <Text style={styles.permIcon}>{p.icon}</Text>
                  <View style={styles.permInfo}>
                    <Text style={styles.permLabel}>{p.label}</Text>
                    <Text style={styles.permDesc}>{p.description}</Text>
                  </View>
                  <View style={[styles.checkbox, isSelected && styles.checkboxChecked]}>
                    {isSelected && <Text style={styles.checkmark}>✓</Text>}
                  </View>
                </View>
              </GlassCard>
            </TouchableOpacity>
          );
        })}

        <View style={styles.saveSection}>
          <Button
            title="Save Permissions"
            onPress={handleSave}
            loading={loading}
            variant="primary"
            size="lg"
            fullWidth
          />
        </View>
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
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
  quickActions: { flexDirection: 'row', gap: 8, paddingHorizontal: spacing.lg, marginTop: spacing.md, marginBottom: spacing.sm },
  quickBtn: { flex: 1, backgroundColor: colors.bgCard, padding: 12, borderRadius: 12, alignItems: 'center', borderWidth: 1, borderColor: colors.border },
  quickText: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  selectedCount: { fontSize: 13, color: colors.textMuted, fontWeight: '500', paddingHorizontal: spacing.lg, marginBottom: spacing.sm },
  permRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  permIcon: { fontSize: 22, width: 30, textAlign: 'center' },
  permInfo: { flex: 1 },
  permLabel: { fontSize: 15, fontWeight: '600', color: colors.textPrimary },
  permDesc: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  checkbox: { width: 24, height: 24, borderRadius: 7, borderWidth: 2, borderColor: colors.border, justifyContent: 'center', alignItems: 'center' },
  checkboxChecked: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkmark: { color: colors.textInverse, fontSize: 14, fontWeight: '700' },
  saveSection: { paddingHorizontal: spacing.lg, marginTop: spacing.xxl },
});
