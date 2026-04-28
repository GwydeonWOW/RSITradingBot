import { useEffect, useRef, useCallback, useState } from "react";

type MessageHandler = (data: unknown) => void;

interface UseWebSocketOptions {
  url: string;
  onMessage: MessageHandler;
  reconnectInterval?: number;
  enabled?: boolean;
}

export function useWebSocket({
  url,
  onMessage,
  reconnectInterval = 5000,
  enabled = true,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number | null>(null);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");

  const connect = useCallback(() => {
    if (!enabled) return;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;
      setStatus("connecting");

      ws.onopen = () => {
        setStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string);
          onMessage(data);
        } catch {
          // Non-JSON message, ignore
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
        wsRef.current = null;
        reconnectTimer.current = setTimeout(connect, reconnectInterval);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      reconnectTimer.current = setTimeout(connect, reconnectInterval);
    }
  }, [url, onMessage, reconnectInterval, enabled]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current !== null) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { status };
}
