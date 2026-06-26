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
import { staffApi } from '../../services/staffApi';

interface StaffMember {
  id: number;
  user_id: number;
  name: string;
  phone: string;
  email?: string;
  role: 'owner' | 'manager' | 'staff';
  permissions: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export default function StaffListScreen({ navigation }: any) {
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStaff = async (isRefresh = false) => {
    try {
      if (!isRefresh) {
        setLoading(true);
      }
      setError(null);

      const response = await staffApi.getStaff();
      setStaff(response.data.staff);
    } catch (err: any) {
      setError(err.message || 'Failed to load staff');
      console.error('Staff fetch error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStaff();
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchStaff(true);
  }, []);

  const handleDeleteStaff = (staffMember: StaffMember) => {
    if (staffMember.role === 'owner') {
      Alert.alert('Error', 'Cannot delete owner');
      return;
    }

    Alert.alert(
      'Delete Staff',
      `Are you sure you want to delete ${staffMember.name}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await staffApi.deleteStaff(staffMember.id);
              Alert.alert('Success', 'Staff member deleted successfully');
              fetchStaff();
            } catch (err: any) {
              Alert.alert('Error', err.message || 'Failed to delete staff');
            }
          },
        },
      ]
    );
  };

  const getRoleColor = (role: string): string => {
    switch (role) {
      case 'owner':
        return '#8B5CF6';
      case 'manager':
        return '#3B82F6';
      case 'staff':
        return '#10B981';
      default:
        return '#6B7280';
    }
  };

  const getRoleIcon = (role: string): string => {
    switch (role) {
      case 'owner':
        return '👑';
      case 'manager':
        return '👔';
      case 'staff':
        return '👤';
      default:
        return '👤';
    }
  };

  if (loading) {
    return (
      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Staff Management</Text>
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#10B981" />
          <Text style={styles.loadingText}>Loading staff...</Text>
        </View>
      </ScrollView>
    );
  }

  if (error && !staff.length) {
    return (
      <ScrollView
        style={styles.container}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Staff Management</Text>
        </View>
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={() => fetchStaff()}>
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
        <Text style={styles.headerTitle}>Staff Management</Text>
      </View>

      {/* Action Buttons */}
      <View style={styles.section}>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => navigation.navigate('AddStaff')}
        >
          <Text style={styles.addButtonText}>➕ Add Staff Member</Text>
        </TouchableOpacity>
      </View>

      {/* Staff List */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Team Members ({staff.length})</Text>
        {staff.map((member) => (
          <View key={member.id} style={styles.staffCard}>
            <View style={styles.staffHeader}>
              <View style={styles.staffIconContainer}>
                <Text style={styles.staffIcon}>{getRoleIcon(member.role)}</Text>
              </View>
              <View style={styles.staffInfo}>
                <Text style={styles.staffName}>{member.name}</Text>
                <Text style={styles.staffPhone}>{member.phone}</Text>
                {member.email && (
                  <Text style={styles.staffEmail}>{member.email}</Text>
                )}
              </View>
              <View style={[
                styles.roleBadge,
                { backgroundColor: getRoleColor(member.role) }
              ]}>
                <Text style={styles.roleText}>{member.role}</Text>
              </View>
            </View>

            <View style={styles.staffDetails}>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Permissions:</Text>
                <Text style={styles.detailValue}>
                  {member.permissions.length} modules
                </Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Status:</Text>
                <View style={[
                  styles.statusBadge,
                  { backgroundColor: member.is_active ? '#10B981' : '#EF4444' }
                ]}>
                  <Text style={styles.statusText}>
                    {member.is_active ? 'Active' : 'Inactive'}
                  </Text>
                </View>
              </View>
            </View>

            <View style={styles.staffActions}>
              <TouchableOpacity
                style={[styles.actionButton, styles.editButton]}
                onPress={() => navigation.navigate('EditStaff', { staff: member })}
              >
                <Text style={styles.actionButtonText}>✏️ Edit</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.actionButton, styles.permissionsButton]}
                onPress={() => navigation.navigate('StaffPermissions', { staff: member })}
              >
                <Text style={styles.actionButtonText}>🔐 Permissions</Text>
              </TouchableOpacity>
              {member.role !== 'owner' && (
                <TouchableOpacity
                  style={[styles.actionButton, styles.deleteButton]}
                  onPress={() => handleDeleteStaff(member)}
                >
                  <Text style={styles.actionButtonText}>🗑️ Delete</Text>
                </TouchableOpacity>
              )}
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
  section: {
    padding: 16,
  },
  addButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 16,
  },
  addButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 12,
  },
  staffCard: {
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
  staffHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  staffIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#F3F4F6',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  staffIcon: {
    fontSize: 24,
  },
  staffInfo: {
    flex: 1,
  },
  staffName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 2,
  },
  staffPhone: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 2,
  },
  staffEmail: {
    fontSize: 14,
    color: '#6B7280',
  },
  roleBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  roleText: {
    fontSize: 12,
    color: 'white',
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  staffDetails: {
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  detailLabel: {
    fontSize: 14,
    color: '#6B7280',
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 12,
    color: 'white',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  staffActions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    flex: 1,
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  editButton: {
    backgroundColor: '#3B82F6',
  },
  permissionsButton: {
    backgroundColor: '#8B5CF6',
  },
  deleteButton: {
    backgroundColor: '#EF4444',
  },
  actionButtonText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
});