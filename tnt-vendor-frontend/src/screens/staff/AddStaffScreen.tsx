// ─── Premium Add Staff ──────────────────────────────────────
// Add staff member with premium design system
// Aligned with backend VendorStaffCreate schema:
//   { name, role, phone, password (required), permissions? }

import React, { useState, useRef } from 'react';
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
import { staffApi } from '../../services/staffApi';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Button from '../../design-system/components/Button';

// Permission modules that vendors can grant to staff
// Matches backend permission structure (dict keys)
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

export default function AddStaffScreen({ navigation }: any) {
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    password: '',
    role: 'staff' as 'manager' | 'staff',
    permissions: {} as Record<string, boolean>,
  });
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useState(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
  });

  const handleAdd = async () => {
    if (!formData.name.trim()) { Alert.alert('Error', 'Name is required'); return; }
    if (!formData.phone.trim()) { Alert.alert('Error', 'Phone is required'); return; }
    if (!formData.password || formData.password.length < 4) {
      Alert.alert('Error', 'Password must be at least 4 characters');
      return;
    }

    // Build permissions dict from selected boolean map
    const permissionsDict: Record<string, boolean> = {};
    Object.entries(formData.permissions).forEach(([key, enabled]) => {
      if (enabled) permissionsDict[key] = true;
    });

    try {
      setLoading(true);
      await staffApi.addStaff({
        name: formData.name.trim(),
        phone: formData.phone.trim(),
        password: formData.password,
        role: formData.role,
        permissions: permissionsDict,
      });
      Alert.alert('Success', 'Staff member added successfully', [
        { text: 'OK', onPress: () => navigation.goBack() },
      ]);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to add staff';
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

  const roles: { key: 'manager' | 'staff'; label: string; icon: string; desc: string }[] = [
    { key: 'manager', label: 'Manager', icon: '👔', desc: 'Can manage orders, menu, and staff' },
    { key: 'staff', label: 'Staff', icon: '👤', desc: 'Basic order and menu access' },
  ];

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Add Staff Member</Text>
        <Text style={styles.headerSubtitle}>Invite a new team member</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        <View style={styles.formSection}>

          {/* Basic Info */}
          <Text style={styles.sectionTitle}><Text style={styles.sectionAccent}>│</Text> Basic Information</Text>
          <GlassCard padding={18} borderRadius={20}>
            <FormField
              label="Full Name *"
              value={formData.name}
              onChange={t => setFormData(prev => ({ ...prev, name: t }))}
              placeholder="e.g. Rahul Sharma"
            />
            <FormField
              label="Phone Number *"
              value={formData.phone}
              onChange={t => setFormData(prev => ({ ...prev, phone: t }))}
              placeholder="+91XXXXXXXXXX"
              keyboard="phone-pad"
            />
            <View style={fieldStyles.group}>
              <Text style={fieldStyles.label}>Password * (min 4 characters)</Text>
              <View style={fieldStyles.passwordRow}>
                <TextInput
                  style={[fieldStyles.input, { flex: 1 }]}
                  value={formData.password}
                  onChangeText={t => setFormData(prev => ({ ...prev, password: t }))}
                  placeholder="Set a login password"
                  placeholderTextColor={colors.textMuted}
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                />
                <TouchableOpacity style={fieldStyles.eyeBtn} onPress={() => setShowPassword(v => !v)}>
                  <Text style={fieldStyles.eyeIcon}>{showPassword ? '🙈' : '👁️'}</Text>
                </TouchableOpacity>
              </View>
            </View>
          </GlassCard>

          {/* Role Selection */}
          <Text style={styles.sectionTitle}><Text style={styles.sectionAccent}>│</Text> Role</Text>
          <GlassCard padding={14} borderRadius={18}>
            <View style={styles.roleRow}>
              {roles.map(r => (
                <TouchableOpacity
                  key={r.key}
                  style={[styles.roleBtn, formData.role === r.key && styles.roleBtnActive]}
                  onPress={() => setFormData(prev => ({ ...prev, role: r.key }))}
                >
                  <Text style={styles.roleIcon}>{r.icon}</Text>
                  <Text style={[styles.roleLabel, formData.role === r.key && styles.roleLabelActive]}>{r.label}</Text>
                  <Text style={[styles.roleDesc, formData.role === r.key && styles.roleDescActive]}>{r.desc}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </GlassCard>

          {/* Permissions */}
          <Text style={styles.sectionTitle}><Text style={styles.sectionAccent}>│</Text> Permissions</Text>
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
            <Button title="Add Staff Member" onPress={handleAdd} loading={loading} variant="primary" size="lg" fullWidth />
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
  label: string;
  value: string;
  onChange: (t: string) => void;
  placeholder: string;
  keyboard?: any;
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
  passwordRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  eyeBtn: {
    backgroundColor: colors.bgSecondary,
    borderRadius: 12,
    width: 48,
    height: 50,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  eyeIcon: { fontSize: 18 },
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
  roleRow: { flexDirection: 'row', gap: 10 },
  roleBtn: {
    flex: 1,
    alignItems: 'center',
    padding: 14,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.bgCard,
  },
  roleBtnActive: { borderColor: colors.primary, backgroundColor: colors.primaryPale },
  roleIcon: { fontSize: 24, marginBottom: 6 },
  roleLabel: { fontSize: 13, fontWeight: '700', color: colors.textSecondary, marginBottom: 4 },
  roleLabelActive: { color: colors.primary },
  roleDesc: { fontSize: 10, color: colors.textMuted, textAlign: 'center' },
  roleDescActive: { color: colors.primary + 'AA' },
  permRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  permIcon: { fontSize: 20, width: 28, textAlign: 'center' },
  permContent: { flex: 1 },
  permLabel: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  permDesc: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 7,
    borderWidth: 2,
    borderColor: colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxChecked: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkmark: { color: colors.textInverse, fontSize: 14, fontWeight: '700' },
  submitSection: { marginTop: spacing.xxl },
});
