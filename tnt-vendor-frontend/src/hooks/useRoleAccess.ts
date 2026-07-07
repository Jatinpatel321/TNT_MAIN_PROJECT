import { useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  hasModuleAccess, 
  hasPermission, 
  hasAnyPermission, 
  hasAllPermissions,
  getAccessibleModules,
  canManageStaff,
  canDelete,
  canWrite,
  isOwner,
  isManagerOrAbove,
  UserRole 
} from '../utils/rbac';

export function useRoleAccess() {
  const { user } = useAuth();
  
  const role = useMemo(() => (user?.role as UserRole) || 'staff', [user?.role]);
  
  const accessibleModules = useMemo(() => getAccessibleModules(role), [role]);
  
  return {
    role,
    user,
    // Module access
    hasModuleAccess: (module: string) => hasModuleAccess(role, module),
    getAccessibleModules: () => accessibleModules,
    
    // Permission checks
    hasPermission: (permission: string) => hasPermission(role, permission),
    hasAnyPermission: (permissions: string[]) => hasAnyPermission(role, permissions),
    hasAllPermissions: (permissions: string[]) => hasAllPermissions(role, permissions),
    
    // Role checks
    isOwner: () => isOwner(role),
    isManagerOrAbove: () => isManagerOrAbove(role),
    canManageStaff: () => canManageStaff(role),
    canDelete: () => canDelete(role),
    canWrite: () => canWrite(role),
    
    // Quick checks for common modules
    canAccessAnalytics: () => hasModuleAccess(role, 'analytics'),
    canAccessSettlements: () => hasModuleAccess(role, 'settlements'),
    canAccessPromotions: () => hasModuleAccess(role, 'promotions'),
    canAccessStaff: () => hasModuleAccess(role, 'staff'),
    canAccessSlots: () => hasModuleAccess(role, 'slots'),
    canAccessOrders: () => hasModuleAccess(role, 'orders'),
    canAccessMenu: () => hasModuleAccess(role, 'menu'),
    canAccessInventory: () => hasModuleAccess(role, 'inventory'),
  };
}