import { useCallback, useEffect, useRef, useState } from "react";
import type { ConnectionStatus, WSMessage } from "../types";

interface UseWebSocketOptions {
  url?: string;
  onMessage?: (msg: WSMessage) => void;
  autoReconnect?: boolean;
}

export function useWebSocket({ url = "ws://localhost:9876/ws/mobile", onMessage, autoReconnect = true }: UseWebSocketOptions = {}) {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setStatus("connected");
      // Send handshake
      ws.send(JSON.stringify({ type: "handshake", payload: {} }));
    };

    ws.onclose = () => {
      setStatus("disconnected");
      wsRef.current = null;
      if (autoReconnect) {
        reconnectTimer.current = setTimeout(connect, 3000);
      }
    };

    ws.onerror = () => {
      setStatus("error");
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        if (msg.type === "handshake_ack") {
          // Connection established with session
          console.log("[WS] Handshake OK:", msg.payload.session_id);
        }
        onMessageRef.current?.(msg);
      } catch {
        console.warn("[WS] Failed to parse message");
      }
    };

    wsRef.current = ws;
  }, [url, autoReconnect]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    autoReconnect = false;
    wsRef.current?.close();
    wsRef.current = null;
    setStatus("disconnected");
  }, []); // eslint-disable-line

  const send = useCallback((msg: WSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else {
      console.warn("[WS] Cannot send - not connected");
    }
  }, []);

  useEffect(() => {
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  return { status, connect, disconnect, send };
}
