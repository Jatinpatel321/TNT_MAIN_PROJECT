// ─── Premium Vendor Profile Screen ──────────────────────────────
// Business verification, ratings, operating hours, gallery

import React, { useRef, useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../context/AuthContext';
import { colors as staticColors, shadows, spacing } from '../../design-system';
const colors = staticColors;
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import StatCard from '../../design-system/components/StatCard';
import { useTheme } from '../../context/ThemeContext';
import { profileApi } from '../../services/profileApi';


export default function ProfileScreen({ navigation }: any) {
  const { user, logout } = useAuth();
  const { colors } = useTheme();
  const styles = getStyles(colors);
  const [profile, setProfile] = useState<any>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await profileApi.getProfile();
      setProfile(res.data);
    } catch (err) {
      console.log('Failed to fetch vendor profile from live endpoint:', err);
    }
  };

  const handleLogout = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: logout },
    ]);
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={[styles.header, { backgroundColor: colors.primary }]}>
          <View style={styles.headerDeco1} />
          <View style={styles.headerDeco2} />
          <View style={styles.profileCircle}>
            <Text style={styles.profileInitial}>
              {profile?.vendor_name?.charAt(0)?.toUpperCase() || user?.vendor_name?.charAt(0)?.toUpperCase() || 'V'}
            </Text>
          </View>
          <Text style={styles.vendorName}>{profile?.vendor_name || user?.vendor_name || 'Your Store'}</Text>
          <View style={styles.statusRow}>
            <StatusPill
              label={user?.role === 'vendor_owner' ? 'Owner' : user?.role === 'vendor_staff' ? 'Staff' : 'Vendor'}
              variant="primary"
              size="sm"
            />
            <StatusPill label={profile?.status === 'active' ? 'Active ✓' : (profile?.status || user?.status || 'Verified ✓')} variant="success" size="sm" />
          </View>
        </View>

      <Animated.View style={{ opacity: fadeAnim, flex: 1 }}>
        {/* Quick Stats */}
        <View style={styles.statsRow}>
          <StatCard value={4.8} label="Rating" suffix=" ★" icon="⭐" color={colors.warning} size="sm" decimal={1} style={{ flexBasis: '30%', flexGrow: 1 }} />
          <StatCard value={150} label="Orders" suffix="+" icon="📦" color={colors.primary} size="sm" style={{ flexBasis: '30%', flexGrow: 1 }} />
          <StatCard value={24} label="Active" suffix=" mo" icon="📅" color={colors.secondary} size="sm" style={{ flexBasis: '30%', flexGrow: 1 }} />
        </View>

        {/* Business Info */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}><Text style={[styles.sectionAccent, { color: colors.primary }]}>│</Text> Business Information</Text>
          <GlassCard padding={16} borderRadius={18}>
            <InfoRow icon="🆔" label="Vendor ID" value={`#${profile?.vendor_id ?? user?.vendor_id ?? 'N/A'}`} />
            <InfoRow icon="🏷️" label="Category" value={profile?.category ?? user?.category ?? 'N/A'} />
            <InfoRow icon="📞" label="Phone" value={profile?.owner_phone ?? user?.phone ?? 'N/A'} />
            <InfoRow icon="👤" label="Owner" value={profile?.owner_name ?? user?.owner_name ?? 'N/A'} last />
          </GlassCard>
        </View>

        {/* Verification */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}><Text style={[styles.sectionAccent, { color: colors.primary }]}>│</Text> Verification & Status</Text>
          <GlassCard padding={16} borderRadius={18}>
            <View style={styles.verifRow}>
              <Text style={styles.verifIcon}>✅</Text>
              <View style={styles.verifInfo}>
                <Text style={[styles.verifLabel, { color: colors.textPrimary }]}>Identity Verified</Text>
                <Text style={[styles.verifDesc, { color: colors.textMuted }]}>Your business identity has been verified</Text>
              </View>
              <StatusPill label="Verified" variant="success" size="sm" />
            </View>
          </GlassCard>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}><Text style={[styles.sectionAccent, { color: colors.primary }]}>│</Text> Quick Actions</Text>
          <View style={styles.actionsGrid}>
            <ActionButton icon="🕐" label="Business Hours" onPress={() => navigation?.navigate('BusinessHours')} color={colors.info} />
            <ActionButton icon="📅" label="Holidays" onPress={() => navigation?.navigate('HolidaySettings')} color={colors.warning} />
            <ActionButton icon="👥" label="Staff" onPress={() => navigation?.navigate('StaffManagement')} color={colors.secondary} />
            <ActionButton icon="📦" label="Inventory" onPress={() => navigation?.navigate('InventoryPlanning')} color={colors.aiPrimary} />
          </View>
        </View>

        {/* Sign Out */}
        <TouchableOpacity style={[styles.logoutButton, { backgroundColor: colors.errorPale, borderColor: colors.error + '20' }]} onPress={handleLogout} activeOpacity={0.8}>
          <Text style={[styles.logoutText, { color: colors.error }]}>Sign Out</Text>
        </TouchableOpacity>

        <View style={{ height: 100 }} />
      </Animated.View>
    </ScrollView>
    </SafeAreaView>
  );
}

function InfoRow({ icon, label, value, last = false }: { icon: string; label: string; value: string; last?: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={[infoStyles.row, !last && { borderBottomWidth: 1, borderBottomColor: colors.borderLight }]}>
      <Text style={infoStyles.icon}>{icon}</Text>
      <Text style={[infoStyles.label, { color: colors.textSecondary }]}>{label}</Text>
      <Text style={[infoStyles.value, { color: colors.textPrimary }]}>{value}</Text>
    </View>
  );
}

const infoStyles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, gap: 10 },
  icon: { fontSize: 18, width: 28 },
  label: { flex: 1, fontSize: 14, fontWeight: '500' },
  value: { fontSize: 14, fontWeight: '600' },
});

function ActionButton({ icon, label, onPress, color }: { icon: string; label: string; onPress: () => void; color: string }) {
  const { colors } = useTheme();

  return (
    <TouchableOpacity style={[actionStyles.button, { backgroundColor: colors.bgCard, borderColor: colors.border }]} onPress={onPress} activeOpacity={0.8}>
      <View style={[actionStyles.iconWrap, { backgroundColor: color + '15' }]}>
        <Text style={actionStyles.icon}>{icon}</Text>
      </View>
      <Text style={[actionStyles.label, { color: colors.textPrimary }]}>{label}</Text>
    </TouchableOpacity>
  );
}

const actionStyles = StyleSheet.create({
  button: { flexDirection: 'row', alignItems: 'center', width: '48%', padding: 10, borderRadius: 16, borderWidth: 1, gap: 10, marginBottom: 10 },
  iconWrap: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  icon: { fontSize: 20 },
  label: { fontSize: 12, fontWeight: '600' },
});


const getStyles = (colors: any) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xxl,
    alignItems: 'center',
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  profileCircle: {
    width: 80,
    height: 80,
    borderRadius: 28,
    backgroundColor: 'rgba(255,255,255,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 3,
    borderColor: 'rgba(255,255,255,0.3)',
  },
  profileInitial: { fontSize: 34, fontWeight: '700', color: colors.textInverse },
  vendorName: { fontSize: 24, fontWeight: '700', color: colors.textInverse, marginBottom: 8 },
  statusRow: { flexDirection: 'row', gap: 8 },
  // Sit cleanly below the header. A negative marginTop pulled these cards up
  // into the purple block and clipped its 28px rounded bottom corners, which
  // read as the stat cards overlapping the vendor-name section.
  statsRow: { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: spacing.lg, marginTop: spacing.md, marginBottom: spacing.sm, gap: spacing.sm },
  section: { paddingHorizontal: spacing.lg, marginBottom: spacing.sm },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.md, marginTop: spacing.sm },
  sectionAccent: { color: colors.primary },
  verifRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  verifIcon: { fontSize: 24 },
  verifInfo: { flex: 1 },
  verifLabel: { fontSize: 15, fontWeight: '600', color: colors.textPrimary },
  verifDesc: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  actionsGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', paddingHorizontal: 4 },
  logoutButton: {
    marginHorizontal: spacing.lg,
    marginTop: spacing.md,
    backgroundColor: colors.errorPale,
    padding: 16,
    borderRadius: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.error + '20',
  },
  logoutText: { color: colors.error, fontSize: 16, fontWeight: '700' },
});
