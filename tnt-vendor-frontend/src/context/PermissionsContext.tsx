import React, { createContext, useContext, useState, useEffect } from 'react';
import { staffApi } from '../services/staffApi';

interface Permission {
  module: string;
  actions: string[];
  description: string;
}

interface PermissionsContextType {
  permissions: Permission[];
  loading: boolean;
  hasPermission: (permission: string) => boolean;
  hasModuleAccess: (module: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
}

const PermissionsContext = createContext<PermissionsContextType | undefined>(undefined);

export function PermissionsProvider({ children }: { children: React.ReactNode }) {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPermissions();
  }, []);

  const fetchPermissions = async () => {
    try {
      setLoading(true);
      const response = await staffApi.getPermissions();
      setPermissions(response.data.permissions);
    } catch (err) {
      console.error('Failed to fetch permissions:', err);
    } finally {
      setLoading(false);
    }
  };

  const hasPermission = (permission: string): boolean => {
    // Owner has all permissions
    // For other roles, check if permission exists in available permissions
    const allActions = permissions.flatMap(p => p.actions);
    return allActions.includes(permission);
  };

  const hasModuleAccess = (module: string): boolean => {
    const modulePermission = permissions.find(p => p.module === module);
    return modulePermission !== undefined;
  };

  const hasAnyPermission = (requiredPermissions: string[]): boolean => {
    return requiredPermissions.some(permission => hasPermission(permission));
  };

  const hasAllPermissions = (requiredPermissions: string[]): boolean => {
    return requiredPermissions.every(permission => hasPermission(permission));
  };

  return (
    <PermissionsContext.Provider
      value={{
        permissions,
        loading,
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