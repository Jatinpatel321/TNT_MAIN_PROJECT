import {useEffect, useRef, useCallback, useState} from 'react';
import {AppState, AppStateStatus} from 'react-native';

import {API_BASE_URL} from '../utils/constants';

type WSEvent = {
  event: string;
  data: any;
};

type EventHandler = (event: WSEvent) => void;

const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_DELAY = 1000;
const MAX_DELAY = 30000;

function getWsBaseUrl(): string {
  // Derive WS URL from the HTTP API base URL
  // Replace http:// or https:// with ws:// or wss://
  const base = API_BASE_URL.replace(/^https?:\/\//, '');
  return `ws://${base}`;
}

/**
 * useOrderWebSocket — connects to the real-time order tracking WebSocket.
 *
 * Auth protocol:
 *   1. Open WebSocket to `ws://host/ws/orders/{orderId}`
 *   2. Send `{"token": "<jwt>"}` as first text frame
 *   3. Server replies `{"authenticated": true, "user_id": N}` on success,
 *      or closes with code 4001 on failure.
 *
 * Returns `{isConnected: boolean}` — true once authenticated.
 */
export function useOrderWebSocket(
  orderId: number,
  token: string | null,
  onEvent: EventHandler,
): {isConnected: boolean} {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onEventRef = useRef<EventHandler>(onEvent);
  const [isConnected, setIsConnected] = useState(false);
  const isMountedRef = useRef(true);

  // Keep callback ref current so the WS handler always calls the latest version
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

    // Clean up any existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    try {
      const wsBase = getWsBaseUrl();
      const url = `${wsBase}/ws/orders/${orderId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        // Backend requires JWT in the first text frame
        ws.send(JSON.stringify({token}));
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          // Handle authentication response
          if (msg.authenticated === true) {
            setIsConnected(true);
            return;
          }

          // Handle error frames
          if (msg.error) {
            console.warn('[WS] Server error:', msg.error);
            return;
          }

          // Forward to handler
          onEventRef.current({event: msg.event, data: msg.data});
        } catch (err) {
          console.warn('[WS] Parse error:', err);
        }
      };

      ws.onerror = () => {
        // onclose will fire next, so we let that handle reconnect
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;

        // Code 4001 = auth failure — don't retry
        if (event.code === 4001) {
          console.warn('[WS] Authentication rejected (4001)');
          return;
        }

        // Code 1000 = intentional close (e.g. component unmounting)
        if (!isMountedRef.current || event.code === 1000) return;

        // Exponential backoff reconnect
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            BASE_DELAY * Math.pow(2, reconnectAttemptsRef.current),
            MAX_DELAY,
          );
          reconnectAttemptsRef.current += 1;
          reconnectTimerRef.current = setTimeout(connect, delay);
        }
      };
    } catch (err) {
      console.warn('[WS] Creation error:', err);
    }
  }, [orderId, token]);

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    // Handle app state changes — reconnect when coming to foreground
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
