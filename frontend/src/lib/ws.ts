"use client";

import { useEffect, useRef, useState } from "react";
import { WS_URL } from "./api";

export type WSMessage = { topic: string; payload: unknown };

export function useWebSocket() {
  const [messages, setMessages] = useState<Record<string, unknown>>({});
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let retry = 0;

    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onmessage = (ev) => {
        try {
          const data: WSMessage = JSON.parse(ev.data);
          setMessages((prev) => ({ ...prev, [data.topic]: data.payload }));
        } catch {
          /* ignore */
        }
      };

      ws.onclose = () => {
        if (cancelled) return;
        retry = Math.min(retry + 1, 5);
        setTimeout(connect, 1000 * 2 ** retry);
      };
    };

    connect();
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, []);

  return messages;
}
