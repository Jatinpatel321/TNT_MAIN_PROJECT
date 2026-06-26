import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { staffApi } from '../../services/staffApi';

interface StaffMember {
  id: number;
  name: string;
  role: 'owner' | 'manager' | 'staff';
  permissions: string[];
}

interface Permission {
  module: string;
  actions: string[];
  description: string;
}

export default function StaffPermissionsScreen({ route, navigation }: any) {
  const { staff } = route.params as { staff: StaffMember };
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingPermissions, setLoadingPermissions] = useState(true);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);

  useEffect(() => {
    fetchPermissions();
    setSelectedPermissions([...staff.permissions]);
  }, []);

  const fetchPermissions = async () => {
    try {
      setLoadingPermissions(true);
      const response = await staffApi.getPermissions();
      setPermissions(response.data.permissions);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to load permissions');
    } finally {
      setLoadingPermissions(false);
    }
  };

  const togglePermission = (permission: string) => {
    setSelectedPermissions({
      ...selectedPermissions,
      permissions: selectedPermissions.includes(permission)
        ? selectedPermissions.filter(p => p !== permission)
        : [...selectedPermissions, permission],
    });
  };

  const handleSavePermissions = async () => {
    try {
      setLoading(true);
      await staffApi.updateStaff(staff.id, {
        permissions: selectedPermissions,
      });

      Alert.alert('Success', 'Permissions updated successfully', [
        { text: 'OK', onPress: () => navigation.goBack() }
      ]);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to update permissions');
    } finally {
      setLoading(false);
    }
  };

  const selectAll = () => {
    const allPermissions = permissions.flatMap(p => p.actions);
    setSelectedPermissions(allPermissions);
  };

  const selectNone = () => {
    setSelectedPermissions([]);
  };

  const selectRoleDefaults = () => {
    switch (staff.role) {
      case 'owner':
        selectAll();
        break;
      case 'manager':
        setSelectedPermissions(['orders:read', 'orders:write', 'menu:read', 'menu:write', 'analytics:read', 'inventory:read']);
        break;
      case 'staff':
        setSelectedPermissions(['orders:read', 'menu:read']);
        break;
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Permissions</Text>
        <Text style={styles.headerSubtitle}>{staff.name}</Text>
      </View>

      <View style={styles.infoBox}>
        <Text style={styles.infoIcon}>ℹ️</Text>
        <Text style={styles.infoText}>
          Configure permissions for {staff.name}. Select the modules they can access.
        </Text>
      </View>

      {/* Quick Actions */}
      <View style={styles.section}>
        <View style={styles.quickActions}>
          <TouchableOpacity style={styles.quickActionButton} onPress={selectAll}>
            <Text style={styles.quickActionText}>✅ Select All</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.quickActionButton} onPress={selectNone}>
            <Text style={styles.quickActionText}>❌ Clear All</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.quickActionButton} onPress={selectRoleDefaults}>
            <Text style={styles.quickActionText}>🔄 Role Defaults</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Permissions List */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>
          Available Permissions ({selectedPermissions.length} selected)
        </Text>
        {loadingPermissions ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#10B981" />
            <Text style={styles.loadingText}>Loading permissions...</Text>
          </View>
        ) : (
          permissions.map((permission) => (
            <View key={permission.module} style={styles.permissionCard}>
              <TouchableOpacity
                style={styles.permissionHeader}
                onPress={() => togglePermission(permission.module)}
              >
                <View style={styles.permissionTitleContainer}>
                  <View style={[
                    styles.checkbox,
                    selectedPermissions.includes(permission.module) && styles.checkboxChecked
                  ]}>
                    {selectedPermissions.includes(permission.module) && (
                      <Text style={styles.checkmark}>✓</Text>
                    )}
                  </View>
                  <View style={styles.permissionTitleInfo}>
                    <Text style={styles.permissionModule}>
                      {permission.module.toUpperCase()}
                    </Text>
                    <Text style={styles.permissionDescription}>
                      {permission.description}
                    </Text>
                  </View>
                </View>
              </TouchableOpacity>

              <View style={styles.actionsGrid}>
                {permission.actions.map((action) => {
                  const isSelected = selectedPermissions.includes(action);
                  return (
                    <TouchableOpacity
                      key={action}
                      style={[
                        styles.actionChip,
                        isSelected && styles.actionChipSelected
                      ]}
                      onPress={() => togglePermission(action)}
                    >
                      <Text style={[
                        styles.actionChipText,
                        isSelected && styles.actionChipTextSelected
                      ]}>
                        {action}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
          ))
        )}
      </View>

      {/* Save Button */}
      <View style={styles.section}>
        <TouchableOpacity
          style={[styles.saveButton, loading && styles.saveButtonDisabled]}
          onPress={handleSavePermissions}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.saveButtonText}>Save Permissions</Text>
          )}
        </TouchableOpacity>
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
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: 4,
  },
  infoBox: {
    backgroundColor: '#DBEAFE',
    borderRadius: 12,
    padding: 16,
    margin: 16,
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  infoIcon: {
    fontSize: 20,
    marginRight: 12,
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    color: '#1E40AF',
    lineHeight: 20,
  },
  section: {
    padding: 16,
  },
  quickActions: {
    flexDirection: 'row',
    gap: 8,
  },
  quickActionButton: {
    flex: 1,
    backgroundColor: 'white',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#D1D5DB',
  },
  quickActionText: {
    fontSize: 12,
    color: '#374151',
    fontWeight: '600',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 12,
  },
  permissionCard: {
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
  permissionHeader: {
    marginBottom: 12,
  },
  permissionTitleContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: '#D1D5DB',
    backgroundColor: 'white',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 2,
  },
  checkboxChecked: {
    backgroundColor: '#10B981',
    borderColor: '#10B981',
  },
  checkmark: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  permissionTitleInfo: {
    flex: 1,
  },
  permissionModule: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 4,
  },
  permissionDescription: {
    fontSize: 14,
    color: '#6B7280',
    lineHeight: 18,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 8,
  },
  actionChip: {
    backgroundColor: '#F3F4F6',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  actionChipSelected: {
    backgroundColor: '#D1FAE5',
    borderColor: '#10B981',
  },
  actionChipText: {
    fontSize: 13,
    color: '#6B7280',
    fontWeight: '500',
  },
  actionChipTextSelected: {
    color: '#10B981',
    fontWeight: '600',
  },
  saveButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  saveButtonDisabled: {
    backgroundColor: '#9CA3AF',
  },
  saveButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  loadingContainer: {
    padding: 40,
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 12,
  },
});