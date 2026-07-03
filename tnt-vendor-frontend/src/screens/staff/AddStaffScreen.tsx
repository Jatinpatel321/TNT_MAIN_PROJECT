// ─── Premium Add Staff ──────────────────────────────────────
// Add staff member with premium design system

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Animated,
} from 'react-native';
import { staffApi } from '../../services/staffApi';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Button from '../../design-system/components/Button';

interface Permission { module: string; actions: string[]; description: string; }

export default function AddStaffScreen({ navigation }: any) {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingPerms, setLoadingPerms] = useState(true);
  const [formData, setFormData] = useState({ name: '', phone: '', email: '', role: 'staff' as string, permissions: [] as string[] });
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    (async () => {
      try { const res = await staffApi.getPermissions(); setPermissions(res.data.permissions); }
      catch { } finally { setLoadingPerms(false); }
    })();
  }, []);

  const handleAdd = async () => {
    if (!formData.name || !formData.phone) { Alert.alert('Error', 'Name and Phone required'); return; }
    try {
      setLoading(true);
      await staffApi.addStaff({ name: formData.name, phone: formData.phone, email: formData.email || undefined, role: formData.role as any, permissions: formData.permissions });
      Alert.alert('Success', 'Staff member added', [{ text: 'OK', onPress: () => navigation.goBack() }]);
    } catch (err: any) { Alert.alert('Error', err.message); }
    finally { setLoading(false); }
  };

  const togglePermission = (perm: string) => {
    setFormData(prev => ({ ...prev, permissions: prev.permissions.includes(perm) ? prev.permissions.filter(p => p !== perm) : [...prev.permissions, perm] }));
  };

  const roles = [
    { key: 'owner', label: 'Owner', icon: '👑' },
    { key: 'manager', label: 'Manager', icon: '👔' },
    { key: 'staff', label: 'Staff', icon: '👤' },
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
          <GlassCard padding={18} borderRadius={20}>
            <FormField label="Full Name *" value={formData.name} onChange={t => setFormData(prev => ({ ...prev, name: t }))} placeholder="John Doe" />
            <FormField label="Phone Number *" value={formData.phone} onChange={t => setFormData(prev => ({ ...prev, phone: t }))} placeholder="+91XXXXXXXXXX" keyboard="phone-pad" />
            <FormField label="Email (Optional)" value={formData.email} onChange={t => setFormData(prev => ({ ...prev, email: t }))} placeholder="john@example.com" keyboard="email-address" />
          </GlassCard>

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
                </TouchableOpacity>
              ))}
            </View>
          </GlassCard>

          <Text style={styles.sectionTitle}><Text style={styles.sectionAccent}>│</Text> Permissions</Text>
          {loadingPerms ? (
            <View style={styles.permLoading}><ActivityIndicator size="small" color={colors.primary} /></View>
          ) : (
            permissions.map(p => (
              <TouchableOpacity key={p.module} onPress={() => togglePermission(p.module)}>
                <GlassCard padding={14} borderRadius={16} style={{ marginBottom: 6 }}>
                  <View style={styles.permHeader}>
                    <Text style={styles.permModule}>{p.module.toUpperCase()}</Text>
                    <View style={[styles.checkbox, formData.permissions.includes(p.module) && styles.checkboxChecked]}>
                      {formData.permissions.includes(p.module) && <Text style={styles.checkmark}>✓</Text>}
                    </View>
                  </View>
                  <Text style={styles.permDesc}>{p.description}</Text>
                </GlassCard>
              </TouchableOpacity>
            ))
          )}

          <View style={styles.submitSection}>
            <Button title="Add Staff Member" onPress={handleAdd} loading={loading} variant="primary" size="lg" fullWidth />
          </View>
        </View>
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

function FormField({ label, value, onChange, placeholder, keyboard }: { label: string; value: string; onChange: (t: string) => void; placeholder: string; keyboard?: any }) {
  return (
    <View style={fieldStyles.group}>
      <Text style={fieldStyles.label}>{label}</Text>
      <TextInput style={fieldStyles.input} value={value} onChangeText={onChange} placeholder={placeholder} placeholderTextColor={colors.textMuted} keyboardType={keyboard} autoCapitalize="none" />
    </View>
  );
}

const fieldStyles = StyleSheet.create({
  group: { marginBottom: 14 },
  label: { fontSize: 13, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 },
  input: { backgroundColor: colors.bgSecondary, borderRadius: 12, padding: 14, fontSize: 16, color: colors.textPrimary, borderWidth: 1, borderColor: colors.border },
});

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
  formSection: { padding: spacing.lg },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.md, marginTop: spacing.md },
  sectionAccent: { color: colors.primary },
  roleRow: { flexDirection: 'row', gap: 8 },
  roleBtn: { flex: 1, alignItems: 'center', padding: 12, borderRadius: 14, borderWidth: 1.5, borderColor: colors.border, backgroundColor: colors.bgCard },
  roleBtnActive: { borderColor: colors.primary, backgroundColor: colors.primaryPale },
  roleIcon: { fontSize: 20, marginBottom: 4 },
  roleLabel: { fontSize: 12, fontWeight: '600', color: colors.textSecondary },
  roleLabelActive: { color: colors.primary },
  permLoading: { padding: 20, alignItems: 'center' },
  permHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  permModule: { fontSize: 14, fontWeight: '700', color: colors.textPrimary },
  permDesc: { fontSize: 12, color: colors.textMuted },
  checkbox: { width: 22, height: 22, borderRadius: 6, borderWidth: 2, borderColor: colors.border, justifyContent: 'center', alignItems: 'center' },
  checkboxChecked: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkmark: { color: colors.textInverse, fontSize: 14, fontWeight: '700' },
  submitSection: { marginTop: spacing.xxl },
});
