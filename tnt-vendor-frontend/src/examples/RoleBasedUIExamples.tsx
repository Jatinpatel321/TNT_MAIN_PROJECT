/**
 * Role-Based UI Implementation Examples
 * 
 * This file demonstrates how to use the RBAC components and hooks
 * to protect routes, buttons, actions, and menus based on user roles.
 */

import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { useRoleAccess } from '../hooks/useRoleAccess';
import ProtectedRoute from '../components/ProtectedRoute';
import ProtectedButton from '../components/ProtectedButton';
import ProtectedMenu from '../components/ProtectedMenu';
import { hasModuleAccess, UserRole } from '../utils/rbac';

// Example 1: Using useRoleAccess hook
export function Example1_UseRoleAccessHook() {
  const roleAccess = useRoleAccess();

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Example 1: useRoleAccess Hook</Text>
      
      <Text style={styles.text}>Current Role: {roleAccess.role}</Text>
      
      {/* Check module access */}
      {roleAccess.canAccessAnalytics() && (
        <Text style={styles.success}>✅ Can access Analytics</Text>
      )}
      
      {roleAccess.canAccessSettlements() && (
        <Text style={styles.success}>✅ Can access Settlements</Text>
      )}
      
      {roleAccess.canAccessPromotions() && (
        <Text style={styles.success}>✅ Can access Promotions</Text>
      )}
      
      {roleAccess.canAccessStaff() && (
        <Text style={styles.success}>✅ Can manage Staff</Text>
      )}

      {/* Check permissions */}
      {roleAccess.hasPermission('orders:write') && (
        <Text style={styles.success}>✅ Can write orders</Text>
      )}
      
      {roleAccess.hasPermission('menu:write') && (
        <Text style={styles.success}>✅ Can write menu</Text>
      )}

      {/* Role checks */}
      {roleAccess.isOwner() && (
        <Text style={styles.warning}>👑 You are Owner</Text>
      )}
      
      {roleAccess.canManageStaff() && (
        <Text style={styles.success}>✅ Can manage staff</Text>
      )}
      
      {roleAccess.canDelete() && (
        <Text style={styles.success}>✅ Can delete items</Text>
      )}
    </ScrollView>
  );
}

// Example 2: Using ProtectedRoute
export function Example2_ProtectedRoute() {
  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Example 2: ProtectedRoute Component</Text>
      
      {/* Only owner can access */}
      <ProtectedRoute requiredRole="owner">
        <View style={styles.box}>
          <Text style={styles.success}>👑 Owner Only Content</Text>
        </View>
      </ProtectedRoute>

      {/* Owner or Manager can access */}
      <ProtectedRoute requiredRole={['owner', 'manager']}>
        <View style={styles.box}>
          <Text style={styles.success}>👔 Owner & Manager Content</Text>
        </View>
      </ProtectedRoute>

      {/* Module-based protection */}
      <ProtectedRoute requiredModule="analytics">
        <View style={styles.box}>
          <Text style={styles.success}>📊 Analytics Module Content</Text>
        </View>
      </ProtectedRoute>

      {/* Permission-based protection */}
      <ProtectedRoute requiredPermission="orders:write">
        <View style={styles.box}>
          <Text style={styles.success}>✏️ Can Write Orders Content</Text>
        </View>
      </ProtectedRoute>

      {/* Custom fallback */}
      <ProtectedRoute 
        requiredRole="owner"
        fallback={<Text style={styles.error}>🔒 Custom fallback message</Text>}
      >
        <View style={styles.box}>
          <Text style={styles.success}>Owner Content with Custom Fallback</Text>
        </View>
      </ProtectedRoute>
    </ScrollView>
  );
}

// Example 3: Using ProtectedButton
export function Example3_ProtectedButton() {
  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Example 3: ProtectedButton Component</Text>
      
      {/* Button only for owner */}
      <ProtectedButton
        title="Delete Staff (Owner Only)"
        onPress={() => console.log('Delete staff')}
        requiredRole="owner"
        icon="🗑️"
      />
      
      {/* Button for owner and manager */}
      <ProtectedButton
        title="Edit Menu (Owner & Manager)"
        onPress={() => console.log('Edit menu')}
        requiredRole={['owner', 'manager']}
        icon="✏️"
      />
      
      {/* Button with permission check */}
      <ProtectedButton
        title="Create Order"
        onPress={() => console.log('Create order')}
        permission="orders:write"
        icon="➕"
      />
      
      {/* Button for analytics access */}
      <ProtectedButton
        title="View Analytics"
        onPress={() => console.log('View analytics')}
        requiredRole={['owner', 'manager']}
        icon="📊"
      />
      
      {/* Disabled button example */}
      <ProtectedButton
        title="Disabled Button"
        onPress={() => console.log('Disabled')}
        disabled={true}
        icon="⏸️"
      />
    </ScrollView>
  );
}

// Example 4: Using ProtectedMenu
export function Example4_ProtectedMenu() {
  const menuItems = [
    {
      id: '1',
      title: 'Analytics',
      icon: '📊',
      module: 'analytics',
      requiredRole: ['owner', 'manager'] as UserRole[],
      onPress: () => console.log('Analytics'),
    },
    {
      id: '2',
      title: 'Settlements',
      icon: '💰',
      module: 'settlements',
      requiredRole: 'owner' as UserRole,
      onPress: () => console.log('Settlements'),
    },
    {
      id: '3',
      title: 'Promotions',
      icon: '🎉',
      module: 'promotions',
      requiredRole: 'owner' as UserRole,
      onPress: () => console.log('Promotions'),
    },
    {
      id: '4',
      title: 'Staff',
      icon: '👥',
      module: 'staff',
      requiredRole: 'owner' as UserRole,
      onPress: () => console.log('Staff'),
    },
    {
      id: '5',
      title: 'Orders',
      icon: '📋',
      module: 'orders',
      onPress: () => console.log('Orders'),
    },
    {
      id: '6',
      title: 'Menu',
      icon: '🍽️',
      module: 'menu',
      onPress: () => console.log('Menu'),
    },
  ];

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Example 4: ProtectedMenu Component</Text>
      
      <Text style={styles.subtitle}>
        Menu items are automatically filtered based on user role:
      </Text>
      <Text style={styles.text}>• Owner: All items visible</Text>
      <Text style={styles.text}>• Manager: Analytics, Orders, Menu visible</Text>
      <Text style={styles.text}>• Staff: Orders, Menu only</Text>
      
      <ProtectedMenu items={menuItems} columns={3} />
    </ScrollView>
  );
}

// Example 5: Manual role checking
export function Example5_ManualRoleChecking() {
  const { user } = useAuth();
  const role = user?.role as UserRole;

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Example 5: Manual Role Checking</Text>
      
      {/* Using rbac utilities directly */}
      {hasModuleAccess(role, 'analytics') && (
        <Text style={styles.success}>✅ Can access Analytics</Text>
      )}
      
      {hasModuleAccess(role, 'settlements') && (
        <Text style={styles.success}>✅ Can access Settlements</Text>
      )}
      
      {hasModuleAccess(role, 'promotions') && (
        <Text style={styles.success}>✅ Can access Promotions</Text>
      )}

      {/* Conditional rendering based on role */}
      {role === 'owner' && (
        <View style={styles.box}>
          <Text style={styles.warning}>👑 Owner Features</Text>
          <Text style={styles.text}>• Manage staff</Text>
          <Text style={styles.text}>• Delete anything</Text>
          <Text style={styles.text}>• Full access</Text>
        </View>
      )}
      
      {role === 'manager' && (
        <View style={styles.box}>
          <Text style={styles.info}>👔 Manager Features</Text>
          <Text style={styles.text}>• View analytics</Text>
          <Text style={styles.text}>• Edit orders & menu</Text>
          <Text style={styles.text}>• No staff management</Text>
        </View>
      )}
      
      {role === 'staff' && (
        <View style={styles.box}>
          <Text style={styles.text}>👤 Staff Features</Text>
          <Text style={styles.text}>• View orders</Text>
          <Text style={styles.text}>• View menu</Text>
          <Text style={styles.text}>• Read-only access</Text>
        </View>
      )}
    </ScrollView>
  );
}

// Example 6: Complete screen with RBAC
export function Example6_CompleteScreen() {
  const roleAccess = useRoleAccess();

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Example 6: Complete Screen with RBAC</Text>
      
      {/* Header with role badge */}
      <View style={styles.header}>
        <Text style={styles.headerText}>
          Welcome, {roleAccess.role.toUpperCase()}
        </Text>
      </View>

      {/* Action buttons - protected by role */}
      <View style={styles.buttonRow}>
        <ProtectedButton
          title="Add Item"
          onPress={() => {}}
          permission="orders:write"
          icon="➕"
        />
        
        <ProtectedButton
          title="Edit"
          onPress={() => {}}
          requiredRole={['owner', 'manager']}
          icon="✏️"
        />
        
        <ProtectedButton
          title="Delete"
          onPress={() => {}}
          requiredRole={['owner', 'manager']}
          icon="🗑️"
        />
      </View>

      {/* Conditional sections based on role */}
      {roleAccess.canAccessAnalytics() && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>📊 Analytics Section</Text>
          <Text style={styles.text}>Analytics content visible to owner and manager</Text>
        </View>
      )}

      {roleAccess.canAccessSettlements() && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>💰 Settlements Section</Text>
          <Text style={styles.text}>Settlements content visible to owner only</Text>
        </View>
      )}

      {roleAccess.canAccessPromotions() && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>🎉 Promotions Section</Text>
          <Text style={styles.text}>Promotions content visible to owner only</Text>
        </View>
      )}

      {/* Staff management - owner only */}
      {roleAccess.canAccessStaff() && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>👥 Staff Management</Text>
          <Text style={styles.text}>Staff management visible to owner only</Text>
          <ProtectedButton
            title="Manage Staff"
            onPress={() => {}}
            requiredRole="owner"
            icon="👥"
          />
        </View>
      )}

      {/* Always visible sections */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>📋 Orders</Text>
        <Text style={styles.text}>Orders visible to all roles</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>🍽️ Menu</Text>
        <Text style={styles.text}>Menu visible to all roles</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
    padding: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 16,
    marginTop: 20,
  },
  subtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 12,
    lineHeight: 20,
  },
  text: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 8,
    lineHeight: 20,
  },
  success: {
    fontSize: 14,
    color: '#10B981',
    fontWeight: '600',
    marginBottom: 8,
  },
  error: {
    fontSize: 14,
    color: '#EF4444',
    fontWeight: '600',
    marginBottom: 8,
  },
  warning: {
    fontSize: 14,
    color: '#F59E0B',
    fontWeight: '600',
    marginBottom: 8,
  },
  info: {
    fontSize: 14,
    color: '#3B82F6',
    fontWeight: '600',
    marginBottom: 8,
  },
  box: {
    backgroundColor: 'white',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  header: {
    backgroundColor: '#10B981',
    padding: 20,
    borderRadius: 12,
    marginBottom: 16,
  },
  headerText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: 'white',
    textAlign: 'center',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 16,
  },
  section: {
    backgroundColor: 'white',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 8,
  },
});