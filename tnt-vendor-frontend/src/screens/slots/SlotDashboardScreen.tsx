import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { slotApi } from '../../services/slotApi';

interface Slot {
  id: number;
  start_time: string;
  end_time: string;
  max_orders: number;
  current_orders: number;
  status: string;
  load_label: string;
  available_capacity: number;
  faculty_priority: boolean;
  queue_size: number;
  estimated_wait: number;
  is_ai_recommended: boolean;
}

export default function SlotDashboardScreen({ navigation }: any) {
  const { user } = useAuth();
  const [slots, setSlots] = useState<Slot[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchSlots = async (isRefresh = false) => {
    try {
      if (!isRefresh) {
        setLoading(true);
      }
      setError(null);

      const [slotsRes, analyticsRes] = await Promise.all([
        slotApi.getSlots(),
        slotApi.getAnalytics(),
      ]);

      setSlots(slotsRes.data);
      setAnalytics(analyticsRes.data);
    } catch (err: any) {
      setError(err.message || 'Failed to load slots');
      console.error('Slots fetch error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSlots();
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchSlots(true);
  }, []);

  const handleLockSlot = async (slotId: number) => {
    try {
      await slotApi.lockSlot(slotId);
      Alert.alert('Success', 'Slot locked successfully');
      fetchSlots();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to lock slot');
    }
  };

  const handleUnlockSlot = async (slotId: number) => {
    try {
      await slotApi.unlockSlot(slotId);
      Alert.alert('Success', 'Slot unlocked successfully');
      fetchSlots();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to unlock slot');
    }
  };

  const handleDeleteSlot = (slotId: number) => {
    Alert.alert(
      'Delete Slot',
      'Are you sure you want to delete this slot?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await slotApi.deleteSlot(slotId);
              Alert.alert('Success', 'Slot deleted successfully');
              fetchSlots();
            } catch (err: any) {
              Alert.alert('Error', err.message || 'Failed to delete slot');
            }
          },
        },
      ]
    );
  };

  const getStatusColor = (status: string): string => {
    switch (status.toLowerCase()) {
      case 'available':
        return '#10B981';
      case 'blocked':
        return '#EF4444';
      case 'full':
        return '#F59E0B';
      default:
        return '#6B7280';
    }
  };

  const getLoadLabelColor = (label: string): string => {
    switch (label.toLowerCase()) {
      case 'low':
        return '#10B981';
      case 'medium':
        return '#F59E0B';
      case 'high':
        return '#EF4444';
      default:
        return '#6B7280';
    }
  };

  if (loading) {
    return (
      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Slot Management</Text>
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#10B981" />
          <Text style={styles.loadingText}>Loading slots...</Text>
        </View>
      </ScrollView>
    );
  }

  if (error && !slots.length) {
    return (
      <ScrollView
        style={styles.container}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Slot Management</Text>
        </View>
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={() => fetchSlots()}>
            <Text style={styles.retryButtonText}>Retry</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Slot Management</Text>
      </View>

      {/* Analytics Cards */}
      {analytics && (
        <View style={styles.analyticsGrid}>
          <View style={styles.analyticsCard}>
            <Text style={styles.analyticsValue}>{analytics.total_slots}</Text>
            <Text style={styles.analyticsLabel}>Total Slots</Text>
          </View>
          <View style={styles.analyticsCard}>
            <Text style={styles.analyticsValue}>{analytics.active_slots}</Text>
            <Text style={styles.analyticsLabel}>Active</Text>
          </View>
          <View style={styles.analyticsCard}>
            <Text style={styles.analyticsValue}>{analytics.blocked_slots}</Text>
            <Text style={styles.analyticsLabel}>Blocked</Text>
          </View>
          <View style={styles.analyticsCard}>
            <Text style={styles.analyticsValue}>{Math.round(analytics.utilization_rate * 100)}%</Text>
            <Text style={styles.analyticsLabel}>Utilization</Text>
          </View>
        </View>
      )}

      {/* Action Buttons */}
      <View style={styles.section}>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate('SlotConfiguration')}
        >
          <Text style={styles.actionButtonText}>➕ Create Slots</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, styles.actionButtonSecondary]}
          onPress={() => navigation.navigate('CapacitySettings')}
        >
          <Text style={styles.actionButtonText}>⚙️ Capacity Rules</Text>
        </TouchableOpacity>
      </View>

      {/* Slots List */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Active Slots ({slots.length})</Text>
        {slots.map((slot) => (
          <View key={slot.id} style={styles.slotCard}>
            <View style={styles.slotHeader}>
              <View style={styles.slotTimeContainer}>
                <Text style={styles.slotTime}>
                  {new Date(slot.start_time).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </Text>
                <Text style={styles.slotTimeArrow}>→</Text>
                <Text style={styles.slotTime}>
                  {new Date(slot.end_time).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </Text>
              </View>
              <View style={[
                styles.statusBadge,
                { backgroundColor: getStatusColor(slot.status) }
              ]}>
                <Text style={styles.statusText}>{slot.status}</Text>
              </View>
            </View>

            <View style={styles.slotDetails}>
              <View style={styles.slotDetailRow}>
                <Text style={styles.slotDetailLabel}>Capacity:</Text>
                <Text style={styles.slotDetailValue}>
                  {slot.current_orders}/{slot.max_orders}
                </Text>
              </View>
              <View style={styles.slotDetailRow}>
                <Text style={styles.slotDetailLabel}>Available:</Text>
                <Text style={styles.slotDetailValue}>{slot.available_capacity}</Text>
              </View>
              <View style={styles.slotDetailRow}>
                <Text style={styles.slotDetailLabel}>Load:</Text>
                <Text style={[
                  styles.slotDetailValue,
                  { color: getLoadLabelColor(slot.load_label) }
                ]}>
                  {slot.load_label}
                </Text>
              </View>
              {slot.faculty_priority && (
                <View style={styles.facultyBadge}>
                  <Text style={styles.facultyText}>👨‍🏫 Faculty Priority</Text>
                </View>
              )}
            </View>

            <View style={styles.slotActions}>
              {slot.is_locked ? (
                <TouchableOpacity
                  style={[styles.slotButton, styles.unlockButton]}
                  onPress={() => handleUnlockSlot(slot.id)}
                >
                  <Text style={styles.slotButtonText}>🔓 Unlock</Text>
                </TouchableOpacity>
              ) : (
                <TouchableOpacity
                  style={[styles.slotButton, styles.lockButton]}
                  onPress={() => handleLockSlot(slot.id)}
                >
                  <Text style={styles.slotButtonText}>🔒 Lock</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity
                style={[styles.slotButton, styles.deleteButton]}
                onPress={() => handleDeleteSlot(slot.id)}
              >
                <Text style={styles.slotButtonText}>🗑️ Delete</Text>
              </TouchableOpacity>
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#10B981',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
    marginTop: 100,
  },
  loadingText: {
    fontSize: 16,
    color: '#6B7280',
    marginTop: 12,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
    marginTop: 100,
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  errorText: {
    fontSize: 16,
    color: '#EF4444',
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    backgroundColor: '#10B981',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  analyticsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 16,
    gap: 12,
  },
  analyticsCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  analyticsValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#10B981',
    marginBottom: 4,
  },
  analyticsLabel: {
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 12,
  },
  actionButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 12,
  },
  actionButtonSecondary: {
    backgroundColor: '#3B82F6',
  },
  actionButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  slotCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  slotHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  slotTimeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  slotTime: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  slotTimeArrow: {
    fontSize: 16,
    color: '#6B7280',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  statusText: {
    fontSize: 12,
    color: 'white',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  slotDetails: {
    marginBottom: 12,
  },
  slotDetailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  slotDetailLabel: {
    fontSize: 14,
    color: '#6B7280',
  },
  slotDetailValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
  },
  facultyBadge: {
    backgroundColor: '#FEF3C7',
    padding: 8,
    borderRadius: 6,
    marginTop: 8,
  },
  facultyText: {
    fontSize: 12,
    color: '#92400E',
    fontWeight: '600',
  },
  slotActions: {
    flexDirection: 'row',
    gap: 8,
  },
  slotButton: {
    flex: 1,
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  lockButton: {
    backgroundColor: '#F59E0B',
  },
  unlockButton: {
    backgroundColor: '#10B981',
  },
  deleteButton: {
    backgroundColor: '#EF4444',
  },
  slotButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
});