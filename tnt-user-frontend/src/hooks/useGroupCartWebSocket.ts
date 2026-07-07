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
  const base = API_BASE_URL.replace(/^https?:\/\//, '');
  return `ws://${base}`;
}

/**
 * useGroupCartWebSocket — connects to the real-time group-cart WebSocket,
 * mirroring useOrderWebSocket.
 *
 * Auth protocol:
 *   1. Open WebSocket to `ws://host/ws/groups/{groupId}`
 *   2. Send `{"token": "<jwt>"}` as first text frame
 *   3. Server replies `{"authenticated": true, "user_id": N}` on success,
 *      or closes with code 4001/4003 on failure.
 *
 * Every group change (item added/removed, member joined, slot locked, split
 * finalized, order placed, payment recorded) arrives as an event, letting the
 * screen refresh live instead of polling.
 *
 * Returns `{isConnected: boolean}` — true once authenticated.
 */
export function useGroupCartWebSocket(
  groupId: number,
  token: string | null,
  onEvent: EventHandler,
): {isConnected: boolean} {
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
    if (!token || !isMountedRef.current) return;

    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    try {
      const wsBase = getWsBaseUrl();
      const url = `${wsBase}/v1/ws/groups/${groupId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
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
            console.warn('[GroupWS] Server error:', msg.error);
            return;
          }
          // Ignore ping/pong keepalive frames
          if (msg.type === 'ping' || msg.type === 'pong') return;

          onEventRef.current({event: msg.event, data: msg.data});
        } catch (err) {
          console.warn('[GroupWS] Parse error:', err);
        }
      };

      ws.onerror = () => {
        // onclose will fire next and handle reconnect
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;

        // 4001 = auth failure, 4003 = not a member — don't retry
        if (event.code === 4001 || event.code === 4003) {
          console.warn('[GroupWS] Connection rejected', event.code);
          return;
        }
        if (!isMountedRef.current || event.code === 1000) return;

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
      console.warn('[GroupWS] Creation error:', err);
    }
  }, [groupId, token]);

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
