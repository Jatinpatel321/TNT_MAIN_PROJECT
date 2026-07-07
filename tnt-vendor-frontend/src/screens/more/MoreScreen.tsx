// ─── More Screen ────────────────────────────────────────────────────
// Premium secondary navigation hub — all non-primary features

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../context/AuthContext';
import { usePermissions } from '../../context/PermissionsContext';
import { useTheme, ThemeMode } from '../../context/ThemeContext';
import { colors as staticColors, shadows, spacing } from '../../design-system';
const colors = staticColors;
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import { profileApi } from '../../services/profileApi';

interface MoreItem {
  icon: string;
  label: string;
  screen: string;
  description: string;
  permission?: string;
  color: string;
}

const MORE_SECTIONS: { title: string; items: MoreItem[] }[] = [
  {
    title: 'Business',
    items: [
      { icon: '👤', label: 'Profile', screen: 'Profile', description: 'Manage your business profile', color: colors.primary, permission: 'profile' },
      { icon: '💰', label: 'Settlements', screen: 'Settlements', description: 'View earnings & payouts', color: colors.success, permission: 'settlements' },
      { icon: '🎯', label: 'Promotions', screen: 'Promotions', description: 'Create offers & campaigns', color: colors.warning, permission: 'promotions' },
      { icon: '🧠', label: 'AI Insights', screen: 'AI', description: 'Smart predictions & analytics', color: colors.aiPrimary, permission: 'ai' },
      { icon: '📊', label: 'Smart Demand', screen: 'DemandDashboard', description: 'Demand forecasting', color: colors.secondary, permission: 'analytics' },
    ],
  },
  {
    title: 'Operations',
    items: [
      { icon: '👥', label: 'Staff Management', screen: 'StaffManagement', description: 'Manage team members', color: colors.secondary, permission: 'staff' },
      { icon: '⏰', label: 'Slot Management', screen: 'SlotManagement', description: 'Configure time slots', color: colors.info, permission: 'slots' },
      { icon: '📦', label: 'Inventory AI', screen: 'InventoryPlanning', description: 'AI-powered stock planning', color: colors.aiPrimary, permission: 'inventory' },
      { icon: '🕐', label: 'Business Hours', screen: 'BusinessHours', description: 'Set operating hours', color: colors.warning, permission: 'business_hours' },
      { icon: '📅', label: 'Holiday Settings', screen: 'HolidaySettings', description: 'Manage holidays', color: colors.error, permission: 'business_hours' },
      { icon: '💬', label: 'Complaints', screen: 'Complaints', description: 'Track & resolve support queries', color: colors.error || '#EF4444' },
    ],
  },
  {
    title: 'Media',
    items: [
      { icon: '🖼️', label: 'Cover Image', screen: 'CoverImageUpload', description: 'Upload cover photo', color: colors.primary },
      { icon: '🖌️', label: 'Logo', screen: 'LogoUpload', description: 'Upload business logo', color: colors.secondary },
    ],
  },
];

export default function MoreScreen({ navigation }: any) {
  const { user, logout } = useAuth();
  const { hasPermission } = usePermissions();
  const { mode: themeMode, isDark, setMode: setThemeMode, colors } = useTheme();
  const styles = getStyles(colors);
  const [profile, setProfile] = useState<any>(null);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await profileApi.getProfile();
      setProfile(res.data);
    } catch (err) {
      console.log('Failed to fetch profile in MoreScreen:', err);
    }
  };

  const handleNavigate = (screen: string) => {
    navigation.navigate(screen);
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.headerContent}>
            <View>
              <Text style={styles.headerTitle}>More</Text>
              <Text style={styles.headerSubtitle}>Everything else at your fingertips</Text>
            </View>
            <TouchableOpacity style={styles.profileCircle} onPress={() => handleNavigate('Profile')}>
              <Text style={styles.profileInitial}>
                {profile?.vendor_name?.charAt(0) || user?.vendor_name?.charAt(0) || 'V'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Quick Status */}
        <View style={styles.statusSection}>
          <GlassCard intensity="light" padding={16} borderRadius={20}>
            <View style={styles.statusRow}>
              <View style={styles.statusItem}>
                <Text style={styles.statusValue}>
                  {profile?.vendor_name || user?.vendor_name || 'Vendor'}
                </Text>
                <View style={styles.statusBadgeRow}>
                <StatusPill label={user?.role || 'Staff'} variant="primary" size="sm" />
              </View>
            </View>
            <TouchableOpacity
              style={styles.logoutButton}
              onPress={logout}
            >
              <Text style={styles.logoutText}>Sign Out</Text>
            </TouchableOpacity>
          </View>
        </GlassCard>
      </View>

      {/* Theme Toggle */}
      <View style={styles.statusSection}>
        <GlassCard intensity="light" padding={16} borderRadius={20}>
          <Text style={styles.themeSectionLabel}>🌙 Appearance</Text>
          <View style={styles.themeRow}>
            {(['light', 'dark', 'system'] as ThemeMode[]).map(m => (
              <TouchableOpacity
                key={m}
                style={[
                  styles.themeChip,
                  themeMode === m && styles.themeChipActive,
                ]}
                onPress={() => setThemeMode(m)}
              >
                <Text style={[
                  styles.themeChipText,
                  themeMode === m && styles.themeChipTextActive,
                ]}>
                  {m === 'light' ? '☀️ Light' : m === 'dark' ? '🌙 Dark' : '⚙️ System'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </GlassCard>
      </View>

      {/* Menu Sections */}
      {MORE_SECTIONS.map((section, sectionIndex) => (
        <View key={sectionIndex} style={styles.section}>
          <Text style={styles.sectionTitle}>
            <Text style={styles.sectionAccent}>│</Text> {section.title}
          </Text>
          {section.items.map((item, itemIndex) => {
            // Skip if permission required and not granted
            if (item.permission && !hasPermission(item.permission) && user?.role !== 'vendor_owner') {
              return null;
            }

            return (
              <TouchableOpacity
                key={itemIndex}
                style={styles.menuItem}
                onPress={() => handleNavigate(item.screen)}
                activeOpacity={0.7}
              >
                <View style={[styles.menuIcon, { backgroundColor: item.color + '15' }]}>
                  <Text style={styles.menuEmoji}>{item.icon}</Text>
                </View>
                <View style={styles.menuContent}>
                  <Text style={styles.menuLabel}>{item.label}</Text>
                  <Text style={styles.menuDescription}>{item.description}</Text>
                </View>
                <Text style={styles.menuArrow}>›</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      ))}

      <View style={styles.bottomSpacer} />
      </ScrollView>
    </SafeAreaView>
  );
}

const getStyles = (colors: any) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },

  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.textInverse,
    letterSpacing: -0.3,
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    marginTop: 4,
    fontWeight: '500',
  },
  profileCircle: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: 'rgba(255,255,255,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  profileInitial: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.textInverse,
  },

  statusSection: {
    paddingHorizontal: spacing.lg,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusItem: {
    flex: 1,
  },
  statusValue: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: 6,
  },
  statusBadgeRow: {
    flexDirection: 'row',
  },
  logoutButton: {
    backgroundColor: colors.errorPale,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
  },
  logoutText: {
    color: colors.error,
    fontSize: 14,
    fontWeight: '600',
  },

  section: {
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.sm,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.md,
    marginTop: spacing.sm,
  },
  sectionAccent: {
    color: colors.primary,
    fontSize: 16,
  },

  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bgCard,
    borderRadius: 16,
    padding: 16,
    marginBottom: 8,
    ...shadows.sm,
  },
  menuIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  menuEmoji: {
    fontSize: 22,
  },
  menuContent: {
    flex: 1,
  },
  menuLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  menuDescription: {
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 2,
  },
  menuArrow: {
    fontSize: 22,
    color: colors.textMuted,
    marginLeft: 8,
  },

  bottomSpacer: {
    height: spacing.huge,
  },

  // ── Theme Toggle ─────────────────────────────────────────────
  themeSectionLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.textSecondary,
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  themeRow: {
    flexDirection: 'row',
    gap: 8,
  },
  themeChip: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: colors.bgSecondary,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: colors.border,
  },
  themeChipActive: {
    backgroundColor: colors.primaryPale,
    borderColor: colors.primary,
  },
  themeChipText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.textMuted,
  },
  themeChipTextActive: {
    color: colors.primary,
    fontWeight: '700',
  },
});

