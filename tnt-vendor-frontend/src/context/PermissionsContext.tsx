// ─── Permissions Context ────────────────────────────────────────────────
// Role-based permission checking. Vendors (vendor_owner) have all permissions.
// Staff (vendor_staff) are limited to what's stored in their permissions dict
// (loaded from the StaffMember.permissions field via the auth context / local storage).
// There is NO /permissions endpoint on the backend — permissions are on the StaffMember.

import React, { createContext, useContext, useMemo } from 'react';
import { useAuth } from './AuthContext';

// The modules a staff member can be granted access to
const ALL_PERMISSION_KEYS = [
  'orders', 'menu', 'inventory', 'analytics',
  'slots', 'staff', 'settlements', 'promotions', 'ai',
  'profile', 'business_hours', 'media',
];

interface PermissionsContextType {
  permissions: string[];
  loading: boolean;
  hasPermission: (permission: string) => boolean;
  hasModuleAccess: (module: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
}

const PermissionsContext = createContext<PermissionsContextType | undefined>(undefined);

export function PermissionsProvider({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  // Compute granted permission keys from the current user
  const permissions = useMemo<string[]>(() => {
    if (!user) return [];

    // Owners always have full access
    if (user.role === 'vendor_owner') {
      return ALL_PERMISSION_KEYS;
    }

    // Staff: derive from their permissions dict (keys with truthy values)
    // The permissions dict is loaded from SecureStore via AuthContext's user.staff_permissions
    if (user.role === 'vendor_staff' && user.staff_permissions) {
      return Object.entries(user.staff_permissions)
        .filter(([_, enabled]) => enabled)
        .map(([key]) => key);
    }

    // Fallback: staff with no permissions stored — grant nothing
    return [];
  }, [user]);

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    if (user.role === 'vendor_owner') return true; // owners always allowed
    return permissions.includes(permission);
  };

  const hasModuleAccess = (module: string): boolean => hasPermission(module);

  const hasAnyPermission = (requiredPermissions: string[]): boolean =>
    requiredPermissions.some(p => hasPermission(p));

  const hasAllPermissions = (requiredPermissions: string[]): boolean =>
    requiredPermissions.every(p => hasPermission(p));

  return (
    <PermissionsContext.Provider
      value={{
        permissions,
        loading: isLoading,
        hasPermission,
        hasModuleAccess,
        hasAnyPermission,
        hasAllPermissions,
      }}
    >
      {children}
    </PermissionsContext.Provider>
  );
}

export function usePermissions() {
  const context = useContext(PermissionsContext);
  if (context === undefined) {
    throw new Error('usePermissions must be used within a PermissionsProvider');
  }
  return context;
}
