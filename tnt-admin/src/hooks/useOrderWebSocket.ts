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
      // Backend authenticates on the first frame and expects a JSON object
      // ({"token": "..."}), not the bare token string.
      ws.send(JSON.stringify({ token }));
    };

    ws.onmessage = (event) => {
      if (unmounted.current) return;
      try {
        const msg = JSON.parse(event.data);

        // Control frames — not order updates.
        if (msg.authenticated === true) { setConnected(true); return; }
        if (msg.error) { setError(String(msg.error)); return; }
        if (msg.type === 'ping' || msg.type === 'pong') return;

        // Order events arrive as an envelope: { event, data }. The status lives
        // in `data` and its field name depends on the event type.
        const evt: string | undefined = msg.event;
        const payload = msg.data ?? {};
        const eta: number | undefined = payload.eta_minutes;

        // ETA-only update — keep the last known status.
        if (evt === 'eta_update') {
          setUpdate(prev => (prev ? { ...prev, eta_minutes: eta ?? prev.eta_minutes } : prev));
          return;
        }

        let status: OrderStatus | undefined;
        if (evt === 'status_change') status = payload.new_status;
        else if (evt === 'status' || evt === 'terminal' || evt === 'order_updated') status = payload.status;

        if (!status) return;  // ignore frames without a resolvable status

        setUpdate({
          status,
          updated_at: payload.timestamp ?? new Date().toISOString(),
          eta_minutes: eta,
        });

        // Add to frame log for the live console in OrderDetail
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        setFrames(prev => [...prev.slice(-19), {
          time: timeStr,
          status,
          eta,
        }]);

        // Auto-close on terminal state
        if (TERMINAL_ORDER_STATUSES.includes(status)) {
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