import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import type { OrderStatus } from '../types';
import { TERMINAL_ORDER_STATUSES, WS_BASE_URL } from '../utils/constants';

interface OrderWSUpdate {
  status: OrderStatus;
  updated_at: string;
  eta_minutes?: number;
}

interface UseOrderWebSocketReturn {
  update: OrderWSUpdate | null;
  connected: boolean;
  error: string | null;
  frames: Array<{ time: string; status: OrderStatus; eta?: number }>;
}

export function useOrderWebSocket(orderId: number | null): UseOrderWebSocketReturn {
  const [update, setUpdate] = useState<OrderWSUpdate | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [frames, setFrames] = useState<Array<{ time: string; status: OrderStatus; eta?: number }>>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmounted = useRef(false);
  const token = useAuthStore.getState().token;

  const connect = useCallback(() => {
    if (!orderId || !token || unmounted.current) return;

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close(1000, 'Reconnecting');
      wsRef.current = null;
    }

    const ws = new WebSocket(`${WS_BASE_URL}/v1/ws/orders/${orderId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (unmounted.current) return;
      setConnected(true);
      setError(null);
      reconnectAttempts.current = 0;  // reset backoff on success
      ws.send(token);  // send JWT as first frame
    };

    ws.onmessage = (event) => {
      if (unmounted.current) return;
      try {
        const data: OrderWSUpdate = JSON.parse(event.data);
        setUpdate(data);

        // Add to frame log for the live console in OrderDetail
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        setFrames(prev => [...prev.slice(-19), {
          time: timeStr,
          status: data.status,
          eta: data.eta_minutes,
        }]);

        // Auto-close on terminal state
        if (TERMINAL_ORDER_STATUSES.includes(data.status)) {
          ws.close(1000, 'Terminal state reached');
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => {
      if (unmounted.current) return;
      setError('WebSocket connection error');
      setConnected(false);
    };

    ws.onclose = (event) => {
      if (unmounted.current) return;
      setConnected(false);

      // Clean close (intentional) — do not reconnect
      if (event.wasClean || event.code === 1000) return;

      // Unexpected close — reconnect with exponential backoff (max 30s)
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
      reconnectAttempts.current += 1;
      setError(`Connection lost. Reconnecting in ${Math.round(delay / 1000)}s…`);

      reconnectTimer.current = setTimeout(() => {
        if (!unmounted.current) connect();
      }, delay);
    };
  }, [orderId, token]);

  useEffect(() => {
    unmounted.current = false;
    connect();

    return () => {
      unmounted.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;  // prevent reconnect trigger on unmount
        wsRef.current.close(1000, 'Component unmounted');
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { update, connected, error, frames };
}