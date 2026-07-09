import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Image, Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import LinearGradient from 'react-native-linear-gradient';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { AppTabsParamList, RootStackParamList } from '../../types/navigation';
import type { Order, User, Vendor } from '../../types/models';
import { Screen } from '../../components/Screen';
import { OrderHistoryCard } from '../../components/OrderHistoryCard';
import { logout as apiLogout } from '../../services/authService';
import { getMyOrders } from '../../services/orderService';
import { getVendors } from '../../services/vendorService';
import {
  deleteAccount,
  getFavoriteMenuItems,
  getFavoriteVendors,
  getPreferences,
  getProfile,
  getProfileStats,
  updatePreferences,
} from '../../services/profileService';
import type {
  FavoriteMenuItem,
  FavoriteVendor,
  ProfileStats,
  UserPreferences,
} from '../../services/profileService';
import { toApiError } from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import { useAppTheme } from '../../theme/ThemeContext';
import { API_BASE_URL } from '../../constants/api';
import { formatCurrency } from '../../utils/format';
import {
  ActionRow,
  Chip,
  EmptyState,
  FadeInSection,
  ProfileSkeleton,
  SectionCard,
  StatTile,
  ToggleRow,
} from './profileUi';

type Props = NativeStackScreenProps<AppTabsParamList & RootStackParamList, 'ProfileTab'>;

const DIETARY_LABELS: Record<string, string> = {
  vegetarian: 'Vegetarian',
  non_vegetarian: 'Non-Vegetarian',
  vegan: 'Vegan',
  jain: 'Jain',
  other: 'Other',
};

const CATEGORY_LABELS: Record<string, string> = {
  south_indian: 'South Indian',
  north_indian: 'North Indian',
  chinese: 'Chinese',
  fast_food: 'Fast Food',
  healthy: 'Healthy',
  snacks: 'Snacks',
  beverages: 'Beverages',
};

function memberSinceLabel(createdAt: string | null | undefined): string | null {
  if (!createdAt) return null;
  const d = new Date(createdAt);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
}

export function ProfileScreen({ navigation }: Props) {
  const { logout, user: authUser } = useAuth();
  const { colors, isDark, toggle: toggleTheme } = useAppTheme();

  const [profile, setProfile] = useState<User | null>(null);
  const [stats, setStats] = useState<ProfileStats | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [vendors, setVendors] = useState<Record<number, Vendor>>({});
  const [favoriteVendors, setFavoriteVendors] = useState<FavoriteVendor[]>([]);
  const [favoriteMenuItems, setFavoriteMenuItems] = useState<FavoriteMenuItem[]>([]);
  const [prefs, setPrefs] = useState<UserPreferences>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadAll = useCallback(async (silent = false) => {
    try {
      const [p, s, myOrders, food, stationery, favVendors, favItems, preferences] =
        await Promise.all([
          getProfile(),
          getProfileStats().catch(() => null),
          getMyOrders().catch(() => [] as Order[]),
          getVendors('food').catch(() => [] as Vendor[]),
          getVendors('stationery').catch(() => [] as Vendor[]),
          getFavoriteVendors().catch(() => [] as FavoriteVendor[]),
          getFavoriteMenuItems().catch(() => [] as FavoriteMenuItem[]),
          getPreferences().catch(() => ({} as UserPreferences)),
        ]);
      setProfile(p);
      setStats(s);
      setOrders(myOrders);
      setFavoriteVendors(favVendors);
      setFavoriteMenuItems(favItems);
      setPrefs(preferences);
      const map: Record<number, Vendor> = {};
      [...food, ...stationery].forEach((v) => {
        map[v.id] = v;
      });
      setVendors(map);
    } catch (e) {
      if (!silent) Alert.alert('Failed to load profile', toApiError(e).message);
    }
  }, []);

  useEffect(() => {
    (async () => {
      await loadAll();
      setLoading(false);
    })();
  }, [loadAll]);

  // Refresh silently when returning from EditProfile and other screens.
  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      if (!loading) loadAll(true);
    });
    return unsubscribe;
  }, [navigation, loadAll, loading]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadAll(true);
    setRefreshing(false);
  }, [loadAll]);

  const setPref = useCallback(
    (key: keyof UserPreferences, value: boolean) => {
      // Optimistic toggle; revert on failure.
      setPrefs((prev) => ({ ...prev, [key]: value }));
      updatePreferences({ [key]: value }).catch(() => {
        setPrefs((prev) => ({ ...prev, [key]: !value }));
      });
    },
    [],
  );

  const onToggleDarkMode = useCallback(() => {
    toggleTheme();
    // Persist the account-level copy; theme context persists locally itself.
    updatePreferences({ dark_mode: !isDark }).catch(() => {});
  }, [toggleTheme, isDark]);

  const vendorName = (vendorId: number) => vendors[vendorId]?.name ?? `Vendor #${vendorId}`;

  const onLogout = async () => {
    try {
      await apiLogout();
      await logout();
      navigation.reset({ index: 0, routes: [{ name: 'Auth' as keyof RootStackParamList }] });
    } catch (e) {
      Alert.alert('Logout failed', toApiError(e).message);
    }
  };

  const onDeleteAccount = () => {
    Alert.alert(
      'Delete Account',
      'Your account will be deactivated and you will be signed out everywhere. Order history is retained for billing records. This cannot be undone from the app.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteAccount();
              await logout();
              navigation.reset({ index: 0, routes: [{ name: 'Auth' as keyof RootStackParamList }] });
            } catch (e) {
              Alert.alert('Delete failed', toApiError(e).message);
            }
          },
        },
      ],
    );
  };

  const displayProfile = profile ?? authUser;
  const profileImageUrl = displayProfile?.profile_image
    ? `${API_BASE_URL}${displayProfile.profile_image}`
    : null;
  const displayName = displayProfile?.full_name ?? displayProfile?.name ?? 'User';
  const displayRole = displayProfile?.role
    ? displayProfile.role.charAt(0).toUpperCase() + displayProfile.role.slice(1)
    : '';
  const initials = displayName
    .split(/\s+/)
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
  const memberSince = memberSinceLabel(displayProfile?.created_at ?? stats?.member_since);

  const identityRows = useMemo(() => {
    const rows: { icon: string; label: string; value: string }[] = [];
    if (displayProfile?.university_id) {
      rows.push({ icon: 'badge-account-horizontal', label: 'University ID', value: displayProfile.university_id });
    }
    if (displayProfile?.department) {
      rows.push({ icon: 'school', label: 'Department', value: displayProfile.department });
    }
    if (displayProfile?.semester != null) {
      rows.push({ icon: 'calendar-text', label: 'Semester', value: `Semester ${displayProfile.semester}` });
    }
    if (displayProfile?.phone) {
      rows.push({ icon: 'phone', label: 'Mobile', value: displayProfile.phone });
    }
    if (displayProfile?.email) {
      rows.push({ icon: 'email-outline', label: 'Email', value: displayProfile.email });
    }
    return rows;
  }, [displayProfile]);

  const recentOrders = orders.slice(0, 3);
  const pickupLocations = prefs.preferred_pickup_locations ?? [];
  const favCategories = prefs.favourite_categories ?? [];

  if (loading) {
    return (
      <Screen>
        <ProfileSkeleton />
      </Screen>
    );
  }

  return (
    <Screen scroll refreshing={refreshing} onRefresh={onRefresh}>
      {/* ── Section 1: Profile header ─────────────────────────────────── */}
      <FadeInSection>
        <View style={styles.heroWrap}>
          <LinearGradient
            colors={isDark ? ['#3B3673', '#22224A'] : ['#6C63FF', '#8F7BFF']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.hero}
          >
            <View style={styles.heroTop}>
              <Text style={styles.heroTitle}>My Profile</Text>
              <Pressable
                onPress={() => navigation.navigate('EditProfile' as any)}
                hitSlop={8}
                style={styles.heroEditBtn}
              >
                <MaterialCommunityIcons name="pencil" size={14} color="#FFFFFF" />
                <Text style={styles.heroEditText}>Edit</Text>
              </Pressable>
            </View>

            <View style={styles.heroRow}>
              <Pressable onPress={() => navigation.navigate('EditProfile' as any)}>
                {profileImageUrl ? (
                  <Image source={{ uri: profileImageUrl }} style={styles.avatar} />
                ) : (
                  <View style={[styles.avatar, styles.avatarFallback]}>
                    <Text style={styles.avatarInitials}>{initials || 'U'}</Text>
                  </View>
                )}
                <View style={styles.avatarCamera}>
                  <MaterialCommunityIcons name="camera" size={12} color="#6C63FF" />
                </View>
              </Pressable>
              <View style={{ flex: 1, gap: 3 }}>
                <Text style={styles.heroName} numberOfLines={1}>
                  {displayName}
                </Text>
                <View style={styles.heroBadges}>
                  <View style={styles.roleBadge}>
                    <MaterialCommunityIcons name="account-tag" size={12} color="#FFFFFF" />
                    <Text style={styles.roleBadgeText}>{displayRole}</Text>
                  </View>
                  {memberSince ? (
                    <Text style={styles.memberSince}>Member since {memberSince}</Text>
                  ) : null}
                </View>
              </View>
            </View>
          </LinearGradient>

          <SectionCard style={styles.identityCard}>
            {identityRows.length === 0 ? (
              <EmptyState
                icon="card-account-details-outline"
                title="Complete your profile"
                subtitle="Add your university ID, department and contact details."
              />
            ) : (
              identityRows.map((row, idx) => (
                <View
                  key={row.label}
                  style={[
                    styles.identityRow,
                    idx < identityRows.length - 1 && {
                      borderBottomWidth: StyleSheet.hairlineWidth,
                      borderBottomColor: colors.border,
                    },
                  ]}
                >
                  <MaterialCommunityIcons name={row.icon as any} size={16} color={colors.primary} />
                  <Text style={[styles.identityLabel, { color: colors.muted }]}>{row.label}</Text>
                  <Text style={[styles.identityValue, { color: colors.text }]} numberOfLines={1}>
                    {row.value}
                  </Text>
                </View>
              ))
            )}
          </SectionCard>
        </View>
      </FadeInSection>

      {/* ── Section 2: Campus information ─────────────────────────────── */}
      <FadeInSection delay={60}>
        <SectionCard title="Campus Information" icon="map-marker-radius" style={styles.section}>
          <View style={styles.campusGrid}>
            <View style={styles.campusItem}>
              <Text style={[styles.campusLabel, { color: colors.muted }]}>Campus</Text>
              <Text style={[styles.campusValue, { color: colors.text }]}>
                {displayProfile?.campus ?? 'Not set'}
              </Text>
            </View>
            <View style={styles.campusItem}>
              <Text style={[styles.campusLabel, { color: colors.muted }]}>Residence</Text>
              <Text style={[styles.campusValue, { color: colors.text }]}>
                {displayProfile?.residence_type === 'hostel'
                  ? 'Hostel'
                  : displayProfile?.residence_type === 'day_scholar'
                    ? 'Day Scholar'
                    : 'Not set'}
              </Text>
            </View>
            <View style={styles.campusItem}>
              <Text style={[styles.campusLabel, { color: colors.muted }]}>Dietary Preference</Text>
              <Text style={[styles.campusValue, { color: colors.text }]}>
                {displayProfile?.dietary_preference
                  ? DIETARY_LABELS[displayProfile.dietary_preference] ?? displayProfile.dietary_preference
                  : 'Not set'}
              </Text>
            </View>
          </View>

          {pickupLocations.length > 0 && (
            <View style={styles.chipGroup}>
              <Text style={[styles.chipGroupLabel, { color: colors.muted }]}>Preferred pickup spots</Text>
              <View style={styles.chipRow}>
                {pickupLocations.map((loc) => (
                  <Chip key={loc} label={loc} icon="map-marker" />
                ))}
              </View>
            </View>
          )}

          {favCategories.length > 0 && (
            <View style={styles.chipGroup}>
              <Text style={[styles.chipGroupLabel, { color: colors.muted }]}>Favourite categories</Text>
              <View style={styles.chipRow}>
                {favCategories.map((cat) => (
                  <Chip key={cat} label={CATEGORY_LABELS[cat] ?? cat} icon="silverware-fork-knife" />
                ))}
              </View>
            </View>
          )}
        </SectionCard>
      </FadeInSection>

      {/* ── Section 3: Account statistics ─────────────────────────────── */}
      <FadeInSection delay={120}>
        <View style={styles.section}>
          <Text style={[styles.sectionHeading, { color: colors.text }]}>Account Statistics</Text>
          {stats ? (
            <View style={styles.statsGrid}>
              <StatTile icon="clipboard-list" label="Total Orders" value={String(stats.total_orders)} />
              <StatTile icon="food" label="Food Orders" value={String(stats.food_orders)} />
              <StatTile icon="printer" label="Stationery Orders" value={String(stats.stationery_orders)} />
              <StatTile icon="account-group" label="Group Orders" value={String(stats.group_orders)} />
              <StatTile icon="currency-inr" label="Total Spent" value={formatCurrency(stats.total_spent)} tint={colors.success} />
              <StatTile icon="star-circle" label="Loyalty Points" value={String(Math.floor(stats.loyalty_points))} tint={colors.warning} />
              <StatTile icon="trophy" label="Rewards Earned" value={String(Math.floor(stats.rewards_earned))} tint={colors.warning} />
              <StatTile icon="tag-heart" label="Saved via Offers" value={formatCurrency(stats.saved_via_offers)} tint={colors.success} />
            </View>
          ) : (
            <SectionCard>
              <EmptyState
                icon="chart-donut"
                title="Statistics unavailable"
                subtitle="Pull to refresh to try again."
              />
            </SectionCard>
          )}
        </View>
      </FadeInSection>

      {/* ── Recent orders preview ─────────────────────────────────────── */}
      <FadeInSection delay={160}>
        <View style={styles.section}>
          <View style={styles.sectionHeaderRow}>
            <Text style={[styles.sectionHeading, { color: colors.text }]}>Recent Orders</Text>
            <Pressable onPress={() => navigation.navigate('OrdersTab' as any)} hitSlop={8}>
              <Text style={[styles.sectionLink, { color: colors.primary }]}>View all</Text>
            </Pressable>
          </View>
          {recentOrders.length === 0 ? (
            <SectionCard>
              <EmptyState
                icon="clipboard-text-outline"
                title="No orders yet"
                subtitle="Your recent orders will appear here."
              />
            </SectionCard>
          ) : (
            <View style={{ gap: 10 }}>
              {recentOrders.map((o) => (
                <OrderHistoryCard
                  key={o.id}
                  order={o}
                  vendorName={vendorName(o.vendor_id)}
                  totalAmount={undefined}
                  onPress={() => navigation.navigate('OrderTracking' as any, { orderId: o.id })}
                />
              ))}
            </View>
          )}
        </View>
      </FadeInSection>

      {/* ── Favourites ────────────────────────────────────────────────── */}
      <FadeInSection delay={200}>
        <SectionCard title="Favourites" icon="heart" style={styles.section}>
          {favoriteVendors.length === 0 && favoriteMenuItems.length === 0 ? (
            <EmptyState
              icon="heart-outline"
              title="No favourites yet"
              subtitle="Mark stalls and dishes as favourites to find them here."
            />
          ) : (
            <>
              {favoriteVendors.map((fv, idx) => (
                <ActionRow
                  key={`v-${fv.vendor_id}`}
                  icon="store"
                  label={fv.vendor_name ?? `Vendor #${fv.vendor_id}`}
                  sublabel="Favourite stall"
                  last={idx === favoriteVendors.length - 1 && favoriteMenuItems.length === 0}
                  onPress={() =>
                    navigation.navigate('Menu' as any, { vendorId: fv.vendor_id, vendorName: fv.vendor_name })
                  }
                />
              ))}
              {favoriteMenuItems.map((fi, idx) => (
                <ActionRow
                  key={`i-${fi.menu_item_id}`}
                  icon="food"
                  label={fi.name ?? `Item #${fi.menu_item_id}`}
                  sublabel="Favourite item"
                  last={idx === favoriteMenuItems.length - 1}
                  onPress={() =>
                    fi.vendor_id != null &&
                    navigation.navigate('Menu' as any, { vendorId: fi.vendor_id, vendorName: vendorName(fi.vendor_id) })
                  }
                />
              ))}
            </>
          )}
        </SectionCard>
      </FadeInSection>

      {/* ── Section 4: Quick actions ──────────────────────────────────── */}
      <FadeInSection delay={240}>
        <SectionCard title="Quick Actions" icon="lightning-bolt" style={styles.section}>
          <ActionRow
            icon="history"
            label="Order History"
            sublabel="Track and reorder past orders"
            onPress={() => navigation.navigate('OrdersTab' as any)}
          />
          <ActionRow
            icon="qrcode"
            label="My QR Codes"
            sublabel="Pickup codes for orders that are ready"
            onPress={() => navigation.navigate('MyQRCodes' as any)}
          />
          <ActionRow
            icon="star-circle"
            label="Rewards"
            sublabel="Points, vouchers and redemptions"
            onPress={() => navigation.navigate('RewardsTab' as any)}
          />
          <ActionRow
            icon="ticket-percent"
            label="Redemption History"
            onPress={() => navigation.navigate('RedemptionHistory' as any)}
          />
          <ActionRow
            icon="bell-outline"
            label="Notifications"
            onPress={() => navigation.navigate('NotificationsTab' as any)}
          />
          <ActionRow
            icon="lifebuoy"
            label="Support & Complaints"
            sublabel="Raise and track complaints"
            onPress={() => navigation.navigate('Complaints' as any)}
            last
          />
        </SectionCard>
      </FadeInSection>

      {/* ── Section 5: Preferences ────────────────────────────────────── */}
      <FadeInSection delay={280}>
        <SectionCard title="Preferences" icon="tune" style={styles.section}>
          <ToggleRow
            icon="theme-light-dark"
            label="Dark Mode"
            sublabel="Applies across the app"
            value={isDark}
            onValueChange={onToggleDarkMode}
          />
          <ToggleRow
            icon="run-fast"
            label="Rush Alerts"
            sublabel="Warn me when a stall is in peak rush"
            value={prefs.enable_rush_alerts ?? true}
            onValueChange={(v) => setPref('enable_rush_alerts', v)}
          />
          <ToggleRow
            icon="robot-outline"
            label="AI Recommendations"
            sublabel="Personalized dish and stall suggestions"
            value={prefs.enable_ai_recommendations ?? true}
            onValueChange={(v) => setPref('enable_ai_recommendations', v)}
          />
          <ToggleRow
            icon="autorenew"
            label="Auto Reorder Suggestions"
            sublabel="Smart reorder prompts from past orders"
            value={prefs.enable_reorder_suggestions ?? true}
            onValueChange={(v) => setPref('enable_reorder_suggestions', v)}
          />
          <ToggleRow
            icon="clock-fast"
            label="Off-Peak Reminders"
            sublabel="Nudges about off-peak discounts"
            value={prefs.enable_offpeak_reminders ?? true}
            onValueChange={(v) => setPref('enable_offpeak_reminders', v)}
            last
          />
        </SectionCard>
      </FadeInSection>

      {/* ── Section 6: Security ───────────────────────────────────────── */}
      <FadeInSection delay={320}>
        <SectionCard title="Security" icon="shield-check" style={styles.section}>
          <View style={[styles.securityInfo, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}>
            <MaterialCommunityIcons name="cellphone-key" size={16} color={colors.primary} />
            <Text style={[styles.securityInfoText, { color: colors.subtext }]}>
              You sign in with a one-time password sent to {displayProfile?.phone ?? 'your phone'} — no
              password to manage.
            </Text>
          </View>
          <ActionRow icon="logout" label="Logout" onPress={onLogout} />
          <ActionRow
            icon="account-remove"
            label="Delete Account"
            sublabel="Deactivates your account permanently"
            onPress={onDeleteAccount}
            danger
            last
          />
        </SectionCard>
      </FadeInSection>

      <View style={{ height: 26 }} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  heroWrap: {
    marginTop: 8,
  },
  hero: {
    borderRadius: 22,
    padding: 18,
  },
  heroTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 14,
  },
  heroTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  heroEditBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'rgba(255,255,255,0.22)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
  },
  heroEditText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },
  heroRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 3,
    borderColor: 'rgba(255,255,255,0.65)',
    backgroundColor: '#E5E7EB',
  },
  avatarFallback: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.25)',
  },
  avatarInitials: {
    fontSize: 24,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  avatarCamera: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroName: {
    fontSize: 20,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  heroBadges: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  roleBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(255,255,255,0.22)',
    paddingHorizontal: 9,
    paddingVertical: 3,
    borderRadius: 999,
  },
  roleBadgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
  },
  memberSince: {
    color: 'rgba(255,255,255,0.85)',
    fontSize: 11,
    fontWeight: '600',
  },
  identityCard: {
    marginTop: 12,
  },
  identityRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 9,
  },
  identityLabel: {
    fontSize: 12,
    fontWeight: '600',
    width: 96,
  },
  identityValue: {
    flex: 1,
    fontSize: 13,
    fontWeight: '700',
  },
  section: {
    marginTop: 16,
  },
  sectionHeading: {
    fontSize: 15,
    fontWeight: '800',
    marginBottom: 10,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  sectionLink: {
    fontSize: 13,
    fontWeight: '700',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  campusGrid: {
    gap: 10,
  },
  campusItem: {
    gap: 2,
  },
  campusLabel: {
    fontSize: 12,
    fontWeight: '600',
  },
  campusValue: {
    fontSize: 14,
    fontWeight: '700',
  },
  chipGroup: {
    marginTop: 12,
    gap: 8,
  },
  chipGroupLabel: {
    fontSize: 12,
    fontWeight: '600',
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  securityInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 12,
    marginBottom: 6,
  },
  securityInfoText: {
    flex: 1,
    fontSize: 12,
    lineHeight: 17,
  },
});
