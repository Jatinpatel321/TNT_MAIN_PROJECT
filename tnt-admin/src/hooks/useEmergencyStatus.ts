import { useEffect, useState, useCallback } from 'react';
import { adminApi } from '../api/admin';
import { useUIStore } from '../store/uiStore';
import type { HealthStatus } from '../types';
import { POLL_INTERVAL_HEALTH } from '../utils/constants';

interface UseEmergencyStatusReturn {
  health: HealthStatus | null;
  loading: boolean;
}

export function useEmergencyStatus(): UseEmergencyStatusReturn {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const { setEmergencyShutdown } = useUIStore();

  const checkHealth = useCallback(async () => {
    try {
      const res = await adminApi.getHealth();
      const data = res.data;
      setHealth(data);

      const isShutdown = data.status === 'degraded' || !!data.shutdown_active;
      setEmergencyShutdown(isShutdown);
    } catch {
      // If health check fails, assume potential issue
      setHealth({ status: 'degraded', db: 'error', redis: 'error' });
    } finally {
      setLoading(false);
    }
  }, [setEmergencyShutdown]);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, POLL_INTERVAL_HEALTH);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return { health, loading };
}
