// Role-Based Access Control (RBAC) Utilities

export type UserRole = 'owner' | 'manager' | 'staff';

export interface RolePermissions {
  owner: string[];
  manager: string[];
  staff: string[];
}

// Define which modules each role can access
export const ROLE_MODULE_ACCESS: RolePermissions = {
  owner: ['orders', 'menu', 'inventory', 'analytics', 'promotions', 'settlements', 'slots', 'staff', 'ai'],
  manager: ['orders', 'menu', 'inventory', 'analytics', 'slots'],
  staff: ['orders', 'menu'],
};

// Define which actions each role can perform per module
export const ROLE_ACTIONS: Record<string, Record<string, string[]>> = {
  owner: {
    orders: ['read', 'write', 'delete', 'cancel'],
    menu: ['read', 'write', 'delete'],
    inventory: ['read', 'write', 'update'],
    analytics: ['read', 'export'],
    promotions: ['read', 'write', 'delete'],
    settlements: ['read', 'write'],
    slots: ['read', 'write', 'delete', 'manage'],
    staff: ['read', 'write', 'delete', 'manage'],
    ai: ['read', 'write'],
  },
  manager: {
    orders: ['read', 'write'],
    menu: ['read', 'write'],
    inventory: ['read'],
    analytics: ['read'],
    slots: ['read', 'write'],
  },
  staff: {
    orders: ['read'],
    menu: ['read'],
  },
};

// Check if user has access to a module
export function hasModuleAccess(role: UserRole, module: string): boolean {
  return ROLE_MODULE_ACCESS[role]?.includes(module) ?? false;
}

// Check if user has specific permission (module:action format)
export function hasPermission(role: UserRole, permission: string): boolean {
  const [module, action] = permission.split(':');
  const roleActions = ROLE_ACTIONS[role];
  
  if (!roleActions) return false;
  
  const moduleActions = roleActions[module];
  if (!moduleActions) return false;
  
  // If action is '*', check if module is accessible
  if (action === '*' || action === 'read') {
    return moduleActions.includes('read');
  }
  
  return moduleActions.includes(action);
}

// Check if user has any of the specified permissions
export function hasAnyPermission(role: UserRole, permissions: string[]): boolean {
  return permissions.some(permission => hasPermission(role, permission));
}

// Check if user has all of the specified permissions
export function hasAllPermissions(role: UserRole, permissions: string[]): boolean {
  return permissions.every(permission => hasPermission(role, permission));
}

// Get user's accessible modules
export function getAccessibleModules(role: UserRole): string[] {
  return ROLE_MODULE_ACCESS[role] || [];
}

// Check if user is owner
export function isOwner(role: string): boolean {
  return role === 'owner';
}

// Check if user is manager or above
export function isManagerOrAbove(role: string): boolean {
  return role === 'owner' || role === 'manager';
}

// Check if user can manage staff
export function canManageStaff(role: string): boolean {
  return role === 'owner';
}

// Check if user can delete
export function canDelete(role: string): boolean {
  return role === 'owner' || role === 'manager';
}

// Check if user can write/edit
export function canWrite(role: string): boolean {
  return role === 'owner' || role === 'manager';
}

// Validate JWT role claim
export function validateRoleClaim(role: string | undefined): UserRole | null {
  if (!role) return null;
  
  const validRoles: UserRole[] = ['owner', 'manager', 'staff'];
  if (validRoles.includes(role as UserRole)) {
    return role as UserRole;
  }
  
  return null;
}

// Get role display info
export function getRoleInfo(role: string) {
  switch (role) {
    case 'owner':
      return {
        label: 'Owner',
        icon: '👑',
        color: '#8B5CF6',
        description: 'Full system access',
      };
    case 'manager':
      return {
        label: 'Manager',
        icon: '👔',
        color: '#3B82F6',
        description: 'Limited financial access',
      };
    case 'staff':
      return {
        label: 'Staff',
        icon: '👤',
        color: '#10B981',
        description: 'Operational access only',
      };
    default:
      return {
        label: 'Unknown',
        icon: '👤',
        color: '#6B7280',
        description: 'No access',
      };
  }
}