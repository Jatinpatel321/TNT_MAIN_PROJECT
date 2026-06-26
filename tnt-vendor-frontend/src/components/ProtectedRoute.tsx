import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { hasModuleAccess, UserRole } from '../utils/rbac';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredModule?: string;
  requiredPermission?: string;
  requiredRole?: UserRole | UserRole[];
  fallback?: React.ReactNode;
}

export default function ProtectedRoute({
  children,
  requiredModule,
  requiredPermission,
  requiredRole,
  fallback,
}: ProtectedRouteProps) {
  const { user } = useAuth();

  if (!user) {
    return fallback || <UnauthorizedAccess message="Please log in to access this feature" />;
  }

  const userRole = user.role as UserRole;

  // Check role-based access
  if (requiredRole) {
    const allowedRoles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    if (!allowedRoles.includes(userRole)) {
      return fallback || <UnauthorizedAccess message="You don't have permission to access this feature" />;
    }
  }

  // Check module access
  if (requiredModule && !hasModuleAccess(userRole, requiredModule)) {
    return fallback || <UnauthorizedAccess message="This module is not available for your role" />;
  }

  // Check specific permission
  if (requiredPermission && !hasModuleAccess(userRole, requiredPermission.split(':')[0])) {
    return fallback || <UnauthorizedAccess message="You don't have the required permission" />;
  }

  return <>{children}</>;
}

function UnauthorizedAccess({ message }: { message: string }) {
  return (
    <View style={styles.container}>
      <View style={styles.iconContainer}>
        <Text style={styles.icon}>🔒</Text>
      </View>
      <Text style={styles.message}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#F9FAFB',
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#F3F4F6',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  icon: {
    fontSize: 40,
  },
  message: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 22,
  },
});