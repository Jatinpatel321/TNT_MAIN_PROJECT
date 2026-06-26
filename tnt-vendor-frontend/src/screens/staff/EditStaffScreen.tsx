import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
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
}

interface Permission {
  module: string;
  actions: string[];
  description: string;
}

export default function EditStaffScreen({ route, navigation }: any) {
  const { staff } = route.params;
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingPermissions, setLoadingPermissions] = useState(true);
  const [formData, setFormData] = useState({
    name: staff.name,
    phone: staff.phone,
    email: staff.email || '',
    role: staff.role,
    permissions: [...staff.permissions],
    is_active: staff.is_active,
  });

  useEffect(() => {
    fetchPermissions();
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

  const handleUpdateStaff = async () => {
    if (!formData.name || !formData.phone) {
      Alert.alert('Error', 'Please fill required fields (Name, Phone)');
      return;
    }

    try {
      setLoading(true);
      await staffApi.updateStaff(staff.id, {
        name: formData.name,
        phone: formData.phone,
        email: formData.email || undefined,
        role: formData.role as 'owner' | 'manager' | 'staff',
        permissions: formData.permissions,
        is_active: formData.is_active,
      });

      Alert.alert('Success', 'Staff member updated successfully', [
        { text: 'OK', onPress: () => navigation.goBack() }
      ]);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to update staff');
    } finally {
      setLoading(false);
    }
  };

  const togglePermission = (permission: string) => {
    setFormData({
      ...formData,
      permissions: formData.permissions.includes(permission)
        ? formData.permissions.filter(p => p !== permission)
        : [...formData.permissions, permission],
    });
  };

  const selectRole = (role: 'owner' | 'manager' | 'staff') => {
    setFormData({ ...formData, role });
  };

  const getRolePermissions = (role: string): string[] => {
    switch (role) {
      case 'owner':
        return permissions.flatMap(p => p.actions);
      case 'manager':
        return ['orders:read', 'orders:write', 'menu:read', 'menu:write', 'analytics:read', 'inventory:read'];
      case 'staff':
        return ['orders:read', 'menu:read'];
      default:
        return [];
    }
  };

  const handleRoleSelect = (role: 'owner' | 'manager' | 'staff') => {
    selectRole(role);
    const defaultPermissions = getRolePermissions(role);
    setFormData({
      ...formData,
      role,
      permissions: defaultPermissions,
    });
  };

  const toggleActiveStatus = () => {
    setFormData({ ...formData, is_active: !formData.is_active });
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Edit Staff Member</Text>
      </View>

      <View style={styles.form}>
        {/* Name */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Full Name *</Text>
          <TextInput
            style={styles.input}
            value={formData.name}
            onChangeText={(text) => setFormData({ ...formData, name: text })}
            placeholder="John Doe"
            placeholderTextColor="#9CA3AF"
          />
        </View>

        {/* Phone */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Phone Number *</Text>
          <TextInput
            style={styles.input}
            value={formData.phone}
            onChangeText={(text) => setFormData({ ...formData, phone: text })}
            placeholder="+919999999999"
            placeholderTextColor="#9CA3AF"
            keyboardType="phone-pad"
          />
        </View>

        {/* Email */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Email (Optional)</Text>
          <TextInput
            style={styles.input}
            value={formData.email}
            onChangeText={(text) => setFormData({ ...formData, email: text })}
            placeholder="john@example.com"
            placeholderTextColor="#9CA3AF"
            keyboardType="email-address"
            autoCapitalize="none"
          />
        </View>

        {/* Role Selection */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Role *</Text>
          <View style={styles.roleContainer}>
            <TouchableOpacity
              style={[
                styles.roleButton,
                formData.role === 'owner' && styles.roleButtonActive
              ]}
              onPress={() => handleRoleSelect('owner')}
            >
              <Text style={[
                styles.roleButtonText,
                formData.role === 'owner' && styles.roleButtonTextActive
              ]}>
                👑 Owner
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.roleButton,
                formData.role === 'manager' && styles.roleButtonActive
              ]}
              onPress={() => handleRoleSelect('manager')}
            >
              <Text style={[
                styles.roleButtonText,
                formData.role === 'manager' && styles.roleButtonTextActive
              ]}>
                👔 Manager
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.roleButton,
                formData.role === 'staff' && styles.roleButtonActive
              ]}
              onPress={() => handleRoleSelect('staff')}
            >
              <Text style={[
                styles.roleButtonText,
                formData.role === 'staff' && styles.roleButtonTextActive
              ]}>
                👤 Staff
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Active Status */}
        <View style={styles.formGroup}>
          <TouchableOpacity
            style={[styles.statusToggle, formData.is_active && styles.statusToggleActive]}
            onPress={toggleActiveStatus}
          >
            <Text style={styles.statusToggleText}>
              {formData.is_active ? '✅ Active' : '❌ Inactive'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Permissions */}
        <View style={styles.formGroup}>
          <Text style={styles.label}>Permissions</Text>
          {loadingPermissions ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="small" color="#10B981" />
              <Text style={styles.loadingText}>Loading permissions...</Text>
            </View>
          ) : (
            <View style={styles.permissionsContainer}>
              {permissions.map((permission) => (
                <TouchableOpacity
                  key={permission.module}
                  style={styles.permissionCard}
                  onPress={() => togglePermission(permission.module)}
                >
                  <View style={styles.permissionHeader}>
                    <Text style={styles.permissionModule}>
                      {permission.module.toUpperCase()}
                    </Text>
                    <View style={[
                      styles.checkbox,
                      formData.permissions.includes(permission.module) && styles.checkboxChecked
                    ]}>
                      {formData.permissions.includes(permission.module) && (
                        <Text style={styles.checkmark}>✓</Text>
                      )}
                    </View>
                  </View>
                  <Text style={styles.permissionDescription}>
                    {permission.description}
                  </Text>
                  <View style={styles.actionsContainer}>
                    {permission.actions.map((action) => (
                      <View key={action} style={styles.actionBadge}>
                        <Text style={styles.actionText}>{action}</Text>
                      </View>
                    ))}
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        {/* Submit Button */}
        <TouchableOpacity
          style={[styles.submitButton, loading && styles.submitButtonDisabled]}
          onPress={handleUpdateStaff}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.submitButtonText}>Update Staff Member</Text>
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
  form: {
    padding: 16,
  },
  formGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  input: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#D1D5DB',
    color: '#111827',
  },
  roleContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  roleButton: {
    flex: 1,
    padding: 12,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#D1D5DB',
    backgroundColor: 'white',
    alignItems: 'center',
  },
  roleButtonActive: {
    borderColor: '#10B981',
    backgroundColor: '#F0FDF4',
  },
  roleButtonText: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '600',
  },
  roleButtonTextActive: {
    color: '#10B981',
  },
  statusToggle: {
    backgroundColor: '#F3F4F6',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#D1D5DB',
  },
  statusToggleActive: {
    backgroundColor: '#D1FAE5',
    borderColor: '#10B981',
  },
  statusToggleText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
  },
  permissionsContainer: {
    gap: 12,
  },
  permissionCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    borderWidth: 2,
    borderColor: '#E5E7EB',
  },
  permissionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  permissionModule: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
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
  permissionDescription: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 8,
  },
  actionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  actionBadge: {
    backgroundColor: '#F3F4F6',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  actionText: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  submitButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 20,
  },
  submitButtonDisabled: {
    backgroundColor: '#9CA3AF',
  },
  submitButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  loadingContainer: {
    padding: 20,
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 8,
  },
});