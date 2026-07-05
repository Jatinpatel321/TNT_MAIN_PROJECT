// ─── Premium Edit Staff Screen ────────────────────────────────────
// Edit staff member — aligned with backend VendorStaffUpdate schema:
//   { name?, phone?, role?, is_active?, permissions? }

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  Animated,
} from 'react-native';
import { staffApi, type StaffMember } from '../../services/staffApi';
import { colors, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import Button from '../../design-system/components/Button';

// Same permission list as AddStaffScreen — no API fetch needed
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

/** Convert the staff permissions dict (Record<string, any>) to a boolean map for the UI */
function permDictToMap(perms: StaffMember['permissions']): Record<string, boolean> {
  if (!perms) return {};
  return Object.fromEntries(Object.keys(perms).map(k => [k, true]));
}

export default function EditStaffScreen({ route, navigation }: any) {
  const { staff } = route.params as { staff: StaffMember };
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: staff.name,
    phone: staff.phone,
    role: staff.role as 'manager' | 'staff',
    permissions: permDictToMap(staff.permissions),
    is_active: staff.is_active !== false,
  });
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
  }, []);

  const handleUpdate = async () => {
    if (!formData.name.trim() || !formData.phone.trim()) {
      Alert.alert('Error', 'Name and Phone are required');
      return;
    }
    try {
      setLoading(true);
      // Build permissions dict from boolean map
      const permissionsDict: Record<string, boolean> = {};
      Object.entries(formData.permissions).forEach(([key, enabled]) => {
        if (enabled) permissionsDict[key] = true;
      });

      await staffApi.updateStaff(staff.id, {
        name: formData.name.trim(),
        phone: formData.phone.trim(),
        role: formData.role,
        permissions: permissionsDict,
        is_active: formData.is_active,
      });
      Alert.alert('Success', 'Staff member updated', [
        { text: 'OK', onPress: () => navigation.goBack() },
      ]);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to update staff';
      Alert.alert('Error', msg);
    } finally {
      setLoading(false);
    }
  };

  const togglePermission = (key: string) => {
    setFormData(prev => ({
      ...prev,
      permissions: { ...prev.permissions, [key]: !prev.permissions[key] },
    }));
  };

  const roles: { key: 'manager' | 'staff'; label: string; icon: string }[] = [
    { key: 'manager', label: 'Manager', icon: '👔' },
    { key: 'staff', label: 'Staff', icon: '👤' },
  ];

  const selectedPermCount = Object.values(formData.permissions).filter(Boolean).length;

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Edit Staff</Text>
        <Text style={styles.headerSubtitle}>{staff.name}</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        <View style={styles.formSection}>
          {/* Basic Info */}
          <Text style={styles.sectionTitle}><Text style={styles.sectionAccent}>│</Text> Basic Information</Text>
          <GlassCard padding={18} borderRadius={20}>
            <FormField
              label="Full Name *"
              value={formData.name}
              onChange={t => setFormData(p => ({ ...p, name: t }))}
              placeholder="Staff name"
            />
            <FormField
              label="Phone *"
              value={formData.phone}
              onChange={t => setFormData(p => ({ ...p, phone: t }))}
              placeholder="+91XXXXXXXXXX"
              keyboard="phone-pad"
            />
          </GlassCard>

          {/* Status Toggle */}
          <TouchableOpacity
            style={styles.statusToggle}
            onPress={() => setFormData(p => ({ ...p, is_active: !p.is_active }))}
          >
            <StatusPill
              label={formData.is_active ? 'Active' : 'Inactive'}
              variant={formData.is_active ? 'success' : 'neutral'}
              size="sm"
            />
            <Text style={styles.statusText}>Tap to toggle active status</Text>
          </TouchableOpacity>

          {/* Role Selection */}
          <Text style={styles.sectionTitle}><Text style={styles.sectionAccent}>│</Text> Role</Text>
          <GlassCard padding={14} borderRadius={18}>
            <View style={styles.roleRow}>
              {roles.map(r => (
                <TouchableOpacity
                  key={r.key}
                  style={[styles.roleBtn, formData.role === r.key && styles.roleBtnActive]}
                  onPress={() => setFormData(p => ({ ...p, role: r.key }))}
                >
                  <Text style={styles.roleIcon}>{r.icon}</Text>
                  <Text style={[styles.roleLabel, formData.role === r.key && styles.roleLabelActive]}>
                    {r.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </GlassCard>

          {/* Permissions */}
          <Text style={styles.sectionTitle}>
            <Text style={styles.sectionAccent}>│</Text> Permissions ({selectedPermCount} selected)
          </Text>
          {AVAILABLE_PERMISSIONS.map(p => {
            const isEnabled = !!formData.permissions[p.key];
            return (
              <TouchableOpacity key={p.key} onPress={() => togglePermission(p.key)} activeOpacity={0.7}>
                <GlassCard padding={14} borderRadius={16} style={{ marginBottom: 6 }}>
                  <View style={styles.permRow}>
                    <Text style={styles.permIcon}>{p.icon}</Text>
                    <View style={styles.permContent}>
                      <Text style={styles.permLabel}>{p.label}</Text>
                      <Text style={styles.permDesc}>{p.description}</Text>
                    </View>
                    <View style={[styles.checkbox, isEnabled && styles.checkboxChecked]}>
                      {isEnabled && <Text style={styles.checkmark}>✓</Text>}
                    </View>
                  </View>
                </GlassCard>
              </TouchableOpacity>
            );
          })}

          <View style={styles.submitSection}>
            <Button title="Update Staff Member" onPress={handleUpdate} loading={loading} variant="primary" size="lg" fullWidth />
          </View>
        </View>
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

function FormField({
  label, value, onChange, placeholder, keyboard,
}: {
  label: string; value: string; onChange: (t: string) => void; placeholder: string; keyboard?: any;
}) {
  return (
    <View style={fieldStyles.group}>
      <Text style={fieldStyles.label}>{label}</Text>
      <TextInput
        style={fieldStyles.input}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={colors.textMuted}
        keyboardType={keyboard}
        autoCapitalize="none"
      />
    </View>
  );
}

const fieldStyles = StyleSheet.create({
  group: { marginBottom: 14 },
  label: { fontSize: 13, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 },
  input: {
    backgroundColor: colors.bgSecondary,
    borderRadius: 12,
    padding: 14,
    fontSize: 16,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
  },
});

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
  formSection: { padding: spacing.lg },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.md, marginTop: spacing.md },
  sectionAccent: { color: colors.primary },
  statusToggle: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: spacing.lg, paddingBottom: 0 },
  statusText: { fontSize: 13, color: colors.textMuted, fontWeight: '500' },
  roleRow: { flexDirection: 'row', gap: 8 },
  roleBtn: { flex: 1, alignItems: 'center', padding: 12, borderRadius: 14, borderWidth: 1.5, borderColor: colors.border, backgroundColor: colors.bgCard },
  roleBtnActive: { borderColor: colors.primary, backgroundColor: colors.primaryPale },
  roleIcon: { fontSize: 20, marginBottom: 4 },
  roleLabel: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  roleLabelActive: { color: colors.primary },
  permRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  permIcon: { fontSize: 20, width: 28, textAlign: 'center' },
  permContent: { flex: 1 },
  permLabel: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  permDesc: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  checkbox: { width: 24, height: 24, borderRadius: 7, borderWidth: 2, borderColor: colors.border, justifyContent: 'center', alignItems: 'center' },
  checkboxChecked: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkmark: { color: colors.textInverse, fontSize: 14, fontWeight: '700' },
  submitSection: { marginTop: spacing.xxl },
});
