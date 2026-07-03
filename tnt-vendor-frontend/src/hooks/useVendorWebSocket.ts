import { useEffect, useRef, useCallback, useState } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import { WS_BASE_URL } from '../config/api';

type WSEvent = {
  event: string;
  data: any;
};

type EventHandler = (event: WSEvent) => void;

const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_DELAY = 1000;
const MAX_DELAY = 30000;

/**
 * Vendor WebSocket hook for real-time order updates.
 *
 * Supports two modes:
 *  - **Vendor-wide** (recommended): connect to /ws/vendor/orders which
 *    broadcasts ALL orders for the vendor. Pass orderIds=[] to use this.
 *  - **Per-order**: connect to /ws/orders/<id> for a specific order.
 *
 * Sends JWT as first-frame JSON {token} — matches backend ws_router.py.
 * Uses exponential backoff reconnect with AppState awareness.
 * After MAX_RECONNECT_ATTEMPTS, fires onDisconnected() so callers can
 * show a "tap to refresh" prompt and fall back to polling.
 */
export function useVendorWebSocket(
  orderIds: number[],
  token: string | null,
  onEvent: EventHandler,
  options?: {
    /** Called once WS gives up retrying — caller should show refresh prompt */
    onDisconnected?: () => void;
    /** Connect to vendor-wide channel instead of per-order. Default true when orderIds is empty. */
    useVendorChannel?: boolean;
  },
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onEventRef = useRef<EventHandler>(onEvent);
  const [isConnected, setIsConnected] = useState(false);
  const [reconnectsFailed, setReconnectsFailed] = useState(false);
  const isMountedRef = useRef(true);

  onEventRef.current = onEvent;

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const connect = useCallback(() => {
    if (!token || !isMountedRef.current) return;

    // Choose channel: vendor-wide if explicitly requested OR if no orderIds
    const useVendorCh = options?.useVendorChannel ?? orderIds.length === 0;
    if (!useVendorCh && orderIds.length === 0) return;

    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    const url = useVendorCh
      ? `${WS_BASE_URL}/ws/vendor/orders`
      : `${WS_BASE_URL}/ws/orders/${orderIds[0]}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;
      setReconnectsFailed(false);

      ws.onopen = () => {
        // Send JWT as first text frame — matches backend ws_router.py protocol
        ws.send(JSON.stringify({ token }));
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.authenticated === true) {
            setIsConnected(true);
            return;
          }
          if (msg.error) {
            console.warn('Vendor WS error frame:', msg.error);
            return;
          }
          // Backend emits: { event, data } or { type, ... }
          const evtName = msg.event ?? msg.type;
          if (evtName) {
            onEventRef.current({ event: evtName, data: msg.data ?? msg });
          }
        } catch (err) {
          console.warn('Vendor WS parse error:', err);
        }
      };

      ws.onerror = (err) => {
        console.warn('Vendor WS error:', err);
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;

        if (!isMountedRef.current || event.code === 1000) return;

        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            BASE_DELAY * Math.pow(2, reconnectAttemptsRef.current),
            MAX_DELAY,
          );
          reconnectAttemptsRef.current += 1;
          console.log(`Vendor WS reconnect ${reconnectAttemptsRef.current} in ${delay}ms`);
          reconnectTimerRef.current = setTimeout(connect, delay);
        } else {
          // Exhausted retries — notify caller
          setReconnectsFailed(true);
          options?.onDisconnected?.();
          console.warn('Vendor WS: max reconnect attempts reached');
        }
      };
    } catch (err) {
      console.warn('Vendor WS creation error:', err);
    }
  }, [orderIds.join(','), token, options?.useVendorChannel]);

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    const subscription = AppState.addEventListener(
      'change',
      (state: AppStateStatus) => {
        if (state === 'active' && !wsRef.current && isMountedRef.current) {
          reconnectAttemptsRef.current = 0; // reset backoff on foreground
          connect();
        }
      },
    );

    return () => {
      isMountedRef.current = false;
      disconnect();
      subscription.remove();
    };
  }, [connect, disconnect]);

  return { isConnected, reconnectsFailed };
}
