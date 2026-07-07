// JWT Token Validation Utilities

import { UserRole, validateRoleClaim } from './rbac';

export interface JWTClaims {
  sub?: string;
  role?: string;
  vendor_id?: number;
  exp?: number;
  iat?: number;
  [key: string]: any;
}

/**
 * Decode JWT token payload (without verification - for client-side only)
 * Note: This is for reading claims only. Always verify on backend.
 */
export function decodeJWT(token: string): JWTClaims | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }

    const payload = parts[1];
    // Add padding if needed
    const paddedPayload = payload + '='.repeat((4 - payload.length % 4) % 4);
    const decoded = atob(paddedPayload);
    
    return JSON.parse(decoded);
  } catch (error) {
    console.error('Failed to decode JWT:', error);
    return null;
  }
}

/**
 * Validate JWT token structure and claims
 */
export function validateJWT(token: string): {
  valid: boolean;
  claims: JWTClaims | null;
  role: UserRole | null;
  error?: string;
} {
  try {
    const claims = decodeJWT(token);
    
    if (!claims) {
      return {
        valid: false,
        claims: null,
        role: null,
        error: 'Invalid token format',
      };
    }

    // Check expiration
    if (claims.exp) {
      const isExpired = Date.now() >= claims.exp * 1000;
      if (isExpired) {
        return {
          valid: false,
          claims,
          role: null,
          error: 'Token expired',
        };
      }
    }

    // Validate role claim
    const role = validateRoleClaim(claims.role);
    if (!role) {
      return {
        valid: false,
        claims,
        role: null,
        error: 'Invalid role claim',
      };
    }

    return {
      valid: true,
      claims,
      role,
    };
  } catch (error) {
    return {
      valid: false,
      claims: null,
      role: null,
      error: 'Token validation failed',
    };
  }
}

/**
 * Check if token is expired
 */
export function isTokenExpired(token: string): boolean {
  const claims = decodeJWT(token);
  if (!claims || !claims.exp) {
    return true;
  }
  return Date.now() >= claims.exp * 1000;
}

/**
 * Get token expiration time in seconds
 */
export function getTokenExpiration(token: string): number | null {
  const claims = decodeJWT(token);
  return claims?.exp || null;
}

/**
 * Get time until token expires (in seconds)
 */
export function getTimeUntilExpiration(token: string): number | null {
  const exp = getTokenExpiration(token);
  if (!exp) {
    return null;
  }
  const timeLeft = exp - Math.floor(Date.now() / 1000);
  return Math.max(0, timeLeft);
}

/**
 * Extract role from JWT token
 */
export function extractRoleFromToken(token: string): UserRole | null {
  const claims = decodeJWT(token);
  if (!claims || !claims.role) {
    return null;
  }
  return validateRoleClaim(claims.role);
}

/**
 * Validate token and get user info
 */
export function getValidatedUser(token: string): {
  valid: boolean;
  role: UserRole | null;
  vendorId?: number;
  error?: string;
} {
  const validation = validateJWT(token);
  
  if (!validation.valid) {
    return {
      valid: false,
      role: null,
      error: validation.error,
    };
  }

  return {
    valid: true,
    role: validation.role,
    vendorId: validation.claims?.vendor_id,
  };
}