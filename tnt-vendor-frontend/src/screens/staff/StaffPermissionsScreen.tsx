// ─── Premium Staff Permissions Screen ────────────────────────────
// Manage staff permissions with premium design system

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Animated,
} from 'react-native';
import { staffApi } from '../../services/staffApi';
import { colors, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Button from '../../design-system/components/Button';

interface Permission {
  module: string;
  actions: string[];
  description: string;
}

export default function StaffPermissionsScreen({ route, navigation }: any) {
  const { staff } = route.params;
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingPerms, setLoadingPerms] = useState(true);
  const [selected, setSelected] = useState<string[]>([...(staff.permissions || [])]);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    (async () => {
      try {
        const res = await staffApi.getPermissions();
        setPermissions(res.data.permissions || []);
      } catch { }
      finally { setLoadingPerms(false); }
    })();
  }, []);

  const toggle = (perm: string) => {
    setSelected(prev => prev.includes(perm) ? prev.filter(p => p !== perm) : [...prev, perm]);
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      await staffApi.updateStaff(staff.id, { permissions: selected });
      Alert.alert('Success', 'Permissions updated', [{ text: 'OK', onPress: () => navigation.goBack() }]);
    } catch (err: any) { Alert.alert('Error', err.message); }
    finally { setLoading(false); }
  };

  const selectAll = () => { setSelected(permissions.flatMap(p => p.actions)); };
  const selectNone = () => { setSelected([]); };
  const selectDefaults = () => {
    const defaults: Record<string, string[]> = {
      owner: permissions.flatMap(p => p.actions),
      manager: ['orders:read', 'orders:write', 'menu:read', 'menu:write', 'analytics:read', 'inventory:read'],
      staff: ['orders:read', 'menu:read'],
    };
    setSelected(defaults[staff.role] || []);
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

        <Text style={styles.selectedCount}>{selected.length} permissions selected</Text>

        {/* Permissions List */}
        {loadingPerms ? (
          <View style={styles.loadingWrap}><ActivityIndicator size="large" color={colors.primary} /></View>
        ) : (
          permissions.map(p => (
            <TouchableOpacity key={p.module} onPress={() => toggle(p.module)}>
              <GlassCard padding={14} borderRadius={16} style={{ marginHorizontal: spacing.lg, marginBottom: 6 }}>
                <View style={styles.permHeader}>
                  <View style={styles.permInfo}>
                    <Text style={styles.permModule}>{p.module.toUpperCase()}</Text>
                    <Text style={styles.permDesc}>{p.description}</Text>
                  </View>
                  <View style={[styles.checkbox, selected.includes(p.module) && styles.checkboxChecked]}>
                    {selected.includes(p.module) && <Text style={styles.checkmark}>✓</Text>}
                  </View>
                </View>
                <View style={styles.actionChips}>
                  {p.actions.map(a => {
                    const isSel = selected.includes(a);
                    return (
                      <TouchableOpacity key={a} style={[styles.chip, isSel && styles.chipActive]} onPress={() => toggle(a)}>
                        <Text style={[styles.chipText, isSel && styles.chipTextActive]}>{a}</Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>
              </GlassCard>
            </TouchableOpacity>
          ))
        )}

        <View style={styles.saveSection}>
          <Button title="Save Permissions" onPress={handleSave} loading={loading} variant="primary" size="lg" fullWidth />
        </View>
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    backgroundColor: colors.primary, paddingTop: spacing.huge + 20, paddingBottom: spacing.xxl, paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28, borderBottomRightRadius: 28, overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  quickActions: { flexDirection: 'row', gap: 8, paddingHorizontal: spacing.lg, marginTop: spacing.md, marginBottom: spacing.sm },
  quickBtn: { flex: 1, backgroundColor: colors.bgCard, padding: 12, borderRadius: 12, alignItems: 'center', borderWidth: 1, borderColor: colors.border },
  quickText: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  selectedCount: { fontSize: 13, color: colors.textMuted, fontWeight: '500', paddingHorizontal: spacing.lg, marginBottom: spacing.sm },
  loadingWrap: { padding: 40, alignItems: 'center' },
  permHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  permInfo: { flex: 1 },
  permModule: { fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginBottom: 2 },
  permDesc: { fontSize: 12, color: colors.textMuted },
  checkbox: { width: 22, height: 22, borderRadius: 6, borderWidth: 2, borderColor: colors.border, justifyContent: 'center', alignItems: 'center', marginTop: 2 },
  checkboxChecked: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkmark: { color: colors.textInverse, fontSize: 14, fontWeight: '700' },
  actionChips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 10 },
  chip: { backgroundColor: colors.bgSecondary, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1, borderColor: colors.border },
  chipActive: { backgroundColor: colors.primaryPale, borderColor: colors.primary },
  chipText: { fontSize: 12, color: colors.textMuted, fontWeight: '500' },
  chipTextActive: { color: colors.primary, fontWeight: '600' },
  saveSection: { paddingHorizontal: spacing.lg, marginTop: spacing.xxl },
});
