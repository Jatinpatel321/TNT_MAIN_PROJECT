import { useEffect, useState, useCallback } from 'react';
import { adminApi } from '../api/admin';
import type { AdminAnalytics } from '../types';
import { POLL_INTERVAL_STATS } from '../utils/constants';

interface UseAdminAnalyticsReturn {
  data: AdminAnalytics | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useAdminAnalytics(): UseAdminAnalyticsReturn {
  const [data, setData] = useState<AdminAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      const res = await adminApi.getAnalytics();
      setData(res.data);
      setError(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch analytics';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, POLL_INTERVAL_STATS);
    return () => clearInterval(interval);
  }, [fetch]);

  return { data, loading, error, refresh: fetch };
}
