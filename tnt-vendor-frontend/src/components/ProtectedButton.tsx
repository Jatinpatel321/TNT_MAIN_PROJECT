import React from 'react';
import { TouchableOpacity, Text, StyleSheet, View } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { hasPermission, UserRole } from '../utils/rbac';

interface ProtectedButtonProps {
  title: string;
  onPress: () => void;
  permission?: string;
  requiredRole?: UserRole | UserRole[];
  disabled?: boolean;
  style?: object;
  textStyle?: object;
  icon?: string;
}

export default function ProtectedButton({
  title,
  onPress,
  permission,
  requiredRole,
  disabled = false,
  style,
  textStyle,
  icon,
}: ProtectedButtonProps) {
  const { user } = useAuth();
  
  if (!user) {
    return null;
  }

  const userRole = user.role as UserRole;

  // Check role-based access
  if (requiredRole) {
    const allowedRoles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    if (!allowedRoles.includes(userRole)) {
      return null;
    }
  }

  // Check permission
  if (permission && !hasPermission(userRole, permission)) {
    return null;
  }

  return (
    <TouchableOpacity
      style={[styles.button, disabled && styles.buttonDisabled, style]}
      onPress={onPress}
      disabled={disabled}
    >
      {icon && <Text style={styles.icon}>{icon}</Text>}
      <Text style={[styles.buttonText, textStyle]}>{title}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: '#10B981',
    padding: 14,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  buttonDisabled: {
    backgroundColor: '#9CA3AF',
    opacity: 0.6,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  icon: {
    fontSize: 18,
  },
});