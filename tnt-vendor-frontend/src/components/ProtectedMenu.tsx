import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { hasModuleAccess, UserRole } from '../utils/rbac';

interface MenuItem {
  id: string;
  title: string;
  icon: string;
  module: string;
  requiredRole?: UserRole | UserRole[];
  requiredPermission?: string;
  onPress: () => void;
}

interface ProtectedMenuProps {
  items: MenuItem[];
  columns?: number;
}

export default function ProtectedMenu({ items, columns = 3 }: ProtectedMenuProps) {
  const { user } = useAuth();

  if (!user) {
    return null;
  }

  const userRole = user.role as UserRole;

  // Filter items based on role and permissions
  const visibleItems = items.filter(item => {
    // Check role-based access
    if (item.requiredRole) {
      const allowedRoles = Array.isArray(item.requiredRole) ? item.requiredRole : [item.requiredRole];
      if (!allowedRoles.includes(userRole)) {
        return false;
      }
    }

    // Check module access
    if (item.module && !hasModuleAccess(userRole, item.module)) {
      return false;
    }

    // Check specific permission
    if (item.requiredPermission) {
      const module = item.requiredPermission.split(':')[0];
      if (!hasModuleAccess(userRole, module)) {
        return false;
      }
    }

    return true;
  });

  if (visibleItems.length === 0) {
    return null;
  }

  return (
    <View style={styles.container}>
      {visibleItems.map((item) => (
        <TouchableOpacity
          key={item.id}
          style={styles.menuItem}
          onPress={item.onPress}
        >
          <View style={styles.iconContainer}>
            <Text style={styles.icon}>{item.icon}</Text>
          </View>
          <Text style={styles.title}>{item.title}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 8,
  },
  menuItem: {
    width: `${100 / columns}%`,
    padding: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconContainer: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#F3F4F6',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  icon: {
    fontSize: 28,
  },
  title: {
    fontSize: 12,
    color: '#374151',
    fontWeight: '500',
    textAlign: 'center',
  },
});