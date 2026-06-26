import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, FlatList, Image, Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { AppTabsParamList, RootStackParamList } from '../../types/navigation';
import type { Order, User, Vendor } from '../../types/models';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import { OrderHistoryCard } from '../../components/OrderHistoryCard';
import { getProfile, logout as apiLogout } from '../../services/authService';
import { getMyOrders } from '../../services/orderService';
import { getVendors } from '../../services/vendorService';
import { getPoints } from '../../services/rewardsService';
import type { UserPoints } from '../../types/models';
import { toApiError } from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import { API_BASE_URL } from '../../constants/api';

type Props = NativeStackScreenProps<AppTabsParamList & RootStackParamList, 'ProfileTab'>;

export function ProfileScreen({ navigation }: Props) {
  const { logout, user: authUser } = useAuth();
  const [profile, setProfile] = useState<User | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [vendors, setVendors] = useState<Record<number, Vendor>>({});
  const [rewardPoints, setRewardPoints] = useState<UserPoints | null>(null);
  const [loading, setLoading] = useState(true);
  const [ordersLoading, setOrdersLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [p, myOrders, food, stationery, rp] = await Promise.all([
          getProfile(),
          getMyOrders(),
          getVendors('food'),
          getVendors('stationery'),
          getPoints().catch(() => null),
        ]);
        setProfile(p);
        setOrders(myOrders);
        setRewardPoints(rp);
        const map: Record<number, Vendor> = {};
        [...food, ...stationery].forEach((v) => {
          map[v.id] = v;
        });
        setVendors(map);
      } catch (e) {
        Alert.alert('Failed to load profile', toApiError(e).message);
      } finally {
        setLoading(false);
        setOrdersLoading(false);
      }
    })();
  }, []);

  // Refresh profile when returning from EditProfile
  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', async () => {
      try {
        const p = await getProfile();
        setProfile(p);
      } catch {
        // silently ignore refresh errors
      }
    });
    return unsubscribe;
  }, [navigation]);

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

  const displayProfile = profile ?? authUser;
  const profileImageUrl = displayProfile?.profile_image
    ? `${API_BASE_URL}${displayProfile.profile_image}`
    : null;

  const displayName = displayProfile?.full_name ?? displayProfile?.name ?? 'User';
  const displayRole = displayProfile?.role
    ? displayProfile.role.charAt(0).toUpperCase() + displayProfile.role.slice(1)
    : '';

  const infoItems = [];
  if (displayProfile?.university_id) {
    infoItems.push({ icon: 'badge-account', label: displayProfile.university_id });
  }
  if (displayProfile?.department) {
    infoItems.push({ icon: 'school', label: displayProfile.department });
  }
  if (displayProfile?.semester != null) {
    infoItems.push({ icon: 'calendar-text', label: `Semester ${displayProfile.semester}` });
  }
  infoItems.push({ icon: 'phone', label: displayProfile?.phone ?? '' });
  infoItems.push({ icon: 'account-tag', label: displayRole });

  if (loading) {
    return (
      <Screen>
        <View style={styles.center}>
          <ActivityIndicator size="large" />
        </View>
      </Screen>
    );
  }

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text style={styles.title}>Profile</Text>
        <Pressable
          onPress={() => navigation.navigate('EditProfile' as any)}
          hitSlop={8}
        >
          <MaterialCommunityIcons name="pencil" size={22} color="#6C63FF" />
        </Pressable>
      </View>

      <View style={styles.profileCard}>
        {profileImageUrl ? (
          <Image source={{ uri: profileImageUrl }} style={styles.avatarImage} />
        ) : (
          <View style={styles.avatarPlaceholder}>
            <MaterialCommunityIcons name="account" size={32} color="#6C63FF" />
          </View>
        )}
        <View style={styles.profileInfo}>
          <Text style={styles.name}>{displayName}</Text>
          {infoItems.map((item, idx) => (
            <View key={idx} style={styles.infoRow}>
              <MaterialCommunityIcons name={item.icon as any} size={14} color="#6B7280" />
              <Text style={styles.meta}>{item.label}</Text>
            </View>
          ))}
        </View>
      </View>

      {rewardPoints && (
        <Pressable
          style={styles.rewardsCard}
          onPress={() => navigation.navigate('RewardsTab' as any)}
        >
          <View style={styles.rewardsLeft}>
            <MaterialCommunityIcons name="star-circle" size={22} color="#3B82F6" />
            <View>
              <Text style={styles.rewardsLabel}>Reward Points</Text>
              <Text style={styles.rewardsValue}>{Math.floor(rewardPoints.current_points)} pts</Text>
            </View>
          </View>
          <MaterialCommunityIcons name="chevron-right" size={20} color="#9CA3AF" />
        </Pressable>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>My Orders</Text>
        {ordersLoading ? (
          <View style={styles.center}><ActivityIndicator /></View>
        ) : orders.length === 0 ? (
          <Text style={styles.muted}>No orders yet.</Text>
        ) : (
          <FlatList
            data={orders}
            keyExtractor={(item) => String(item.id)}
            renderItem={({ item }) => (
              <OrderHistoryCard
                order={item}
                vendorName={vendorName(item.vendor_id)}
                totalAmount={undefined}
                onPress={() => navigation.navigate('OrderTracking' as any, { orderId: item.id })}
              />
            )}
            ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
            scrollEnabled={false}
            contentContainerStyle={{ gap: 10 }}
          />
        )}
      </View>

      <View style={styles.actions}>
        <GradientButton label="Logout" onPress={onLogout} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: {
    paddingVertical: 12,
    alignItems: 'center',
  },
  header: {
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
  },
  profileCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 16,
    shadowColor: 'rgba(0,0,0,0.08)',
    shadowOpacity: 0.08,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 8,
    elevation: 4,
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
  },
  avatarImage: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#E5E7EB',
  },
  avatarPlaceholder: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#F3F2FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  profileInfo: {
    flex: 1,
    gap: 4,
  },
  name: {
    fontSize: 17,
    fontWeight: '800',
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  meta: {
    fontSize: 13,
    color: '#4B5563',
  },
  section: {
    marginTop: 16,
    gap: 10,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '800',
  },
  muted: {
    color: '#6B7280',
  },
  actions: {
    marginTop: 18,
    marginBottom: 14,
  },
  rewardsCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    marginTop: 12,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
    elevation: 2,
  },
  rewardsLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  rewardsLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
  },
  rewardsValue: {
    fontSize: 16,
    fontWeight: '800',
    color: '#111827',
  },
});
