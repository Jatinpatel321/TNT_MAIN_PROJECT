import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketMessage {
  event: string;
  data: any;
}

/**
 * Generic WebSocket hook with first-frame JWT auth and exponential
 * backoff reconnect.
 *
 * Auth protocol (matching backend):
 *   1. Open WebSocket to the given URL
 *   2. Send {"token": "<jwt>"} as first text frame
 *   3. Server replies {"authenticated": true} on success
 *   4. Server sends structured events: {"event": "...", "data": {...}}
 */
export function useWebSocket(url: string, token: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  // Use a ref to avoid stale closure issues in callbacks
  const isConnectedRef = useRef(false);

  const connect = useCallback(() => {
    if (!token) {
      console.log('[useWebSocket] No token — skipping connection');
      return;
    }

    try {
      // Close any existing connection
      if (ws.current) {
        ws.current.onclose = null; // prevent reconnect cascade
        ws.current.close();
      }

      // Create new WebSocket — NO token in URL, auth is first-frame
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        // Send JWT as first text frame — backend auth protocol
        ws.current?.send(JSON.stringify({ token }));
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          // Handle authentication response
          if (message.authenticated === true) {
            setIsConnected(true);
            isConnectedRef.current = true;
            reconnectAttempts.current = 0;
            return;
          }

          // Handle error frames
          if (message.error) {
            console.error('[useWebSocket] Auth/Server error:', message.error);
            if (!isConnectedRef.current) {
              // Auth failure before we were ever connected — close
              ws.current?.close();
            }
            return;
          }

          // Forward event to consumer
          setLastMessage(message);
        } catch (error) {
          console.error('[useWebSocket] Failed to parse message:', error);
        }
      };

      ws.current.onerror = () => {
        // onclose fires next, handles reconnect
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        isConnectedRef.current = false;

        // Exponential backoff reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttempts.current),
            30000,
          );
          console.log(
            `[useWebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`,
          );
          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          console.log('[useWebSocket] Max reconnect attempts reached');
        }
      };
    } catch (error) {
      console.error('[useWebSocket] Failed to create connection:', error);
    }
  }, [url, token]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    if (ws.current) {
      ws.current.onclose = null;
      ws.current.close();
      ws.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback(
    (message: any) => {
      if (ws.current && isConnected) {
        ws.current.send(JSON.stringify(message));
      } else {
        console.warn('[useWebSocket] Not connected — cannot send');
      }
    },
    [isConnected],
  );

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
  };
}
