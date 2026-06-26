import {useEffect, useRef, useCallback, useState} from 'react';
import {AppState, AppStateStatus} from 'react-native';

type WSEvent = {
  event: string;
  data: any;
};

type EventHandler = (event: WSEvent) => void;

const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_DELAY = 1000;
const MAX_DELAY = 30000;
const WS_BASE_URL = __DEV__
  ? 'ws://localhost:8000'
  : 'wss://api.tnt-campus.com';

/**
 * Vendor WebSocket hook for real-time order updates.
 *
 * Sends JWT as first-frame JSON (matching backend ws_router.py).
 * Uses exponential backoff reconnect with AppState awareness.
 */
export function useVendorWebSocket(
  orderIds: number[],
  token: string | null,
  onEvent: EventHandler,
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onEventRef = useRef<EventHandler>(onEvent);
  const [isConnected, setIsConnected] = useState(false);
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
    if (!token || !isMountedRef.current || orderIds.length === 0) return;

    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    // Subscribe to the first order — the backend broadcasts all the vendor's
    // orders via a shared channel for real-time vendor dashboard updates.
    try {
      // For a vendor dashboard, we connect to the first order in the list
      // since events are published per-order. In a multi-order scenario,
      // the vendor could subscribe to multiple connections or the backend
      // could expose a vendor-wide channel.
      const primaryOrderId = orderIds[0];
      const url = `${WS_BASE_URL}/ws/orders/${primaryOrderId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        // Send JWT as first text frame — matches backend ws_router.py protocol
        ws.send(JSON.stringify({token}));
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
            console.warn('Vendor WS error:', msg.error);
            return;
          }
          onEventRef.current({event: msg.event, data: msg.data});
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
          console.log(
            `Vendor WS reconnect ${reconnectAttemptsRef.current} in ${delay}ms`,
          );
          reconnectTimerRef.current = setTimeout(connect, delay);
        }
      };
    } catch (err) {
      console.warn('Vendor WS creation error:', err);
    }
  }, [orderIds.join(','), token]);

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    const subscription = AppState.addEventListener(
      'change',
      (state: AppStateStatus) => {
        if (state === 'active' && !wsRef.current && isMountedRef.current) {
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

  return {isConnected};
}
