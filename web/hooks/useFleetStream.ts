"use client";

import { useEffect, useRef, useState } from "react";
import type { WsFrame, Worker } from "@/lib/types";

const STALE_THRESHOLD_MS = 8_000;
const BACKOFF_BASE_MS = 500;
const BACKOFF_MAX_MS = 8_000;

export interface FleetStreamState {
  workers: Worker[];
  degraded: boolean;
  connected: boolean;
  stale: boolean;
}

function wsUrl(): string {
  const envWs =
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_WS_BASE_URL) ||
    (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_WS_BASE_URL);
  const envApi =
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_BASE_URL) ||
    (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_BASE_URL);
  const base = envWs || (envApi ? envApi.replace(/^http/, "ws") : "ws://localhost:8000");
  return `${base}/ws/fleet`;
}

/** contracts/websocket.md — WS /ws/fleet: hello, then a fleet frame on every change. */
export function useFleetStream(): FleetStreamState {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [degraded, setDegraded] = useState(false);
  const [connected, setConnected] = useState(false);
  const [stale, setStale] = useState(false);

  const lastFrameAtRef = useRef<number | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const closedByUsRef = useRef(false);

  useEffect(() => {
    closedByUsRef.current = false;

    const connect = () => {
      let socket: WebSocket;
      try {
        socket = new WebSocket(wsUrl());
      } catch {
        scheduleReconnect();
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => {
        setConnected(true);
        retryRef.current = 0;
      };

      socket.onmessage = (raw) => {
        lastFrameAtRef.current = Date.now();
        setStale(false);
        let frame: WsFrame;
        try {
          frame = JSON.parse(raw.data as string) as WsFrame;
        } catch {
          return;
        }
        if (frame.kind === "fleet") {
          const data = frame.data as { workers: Worker[]; degraded: boolean };
          setWorkers(data.workers);
          setDegraded(data.degraded);
        }
      };

      socket.onclose = () => {
        setConnected(false);
        socketRef.current = null;
        if (!closedByUsRef.current) scheduleReconnect();
      };

      socket.onerror = () => socket.close();
    };

    const scheduleReconnect = () => {
      const delay = Math.min(BACKOFF_MAX_MS, BACKOFF_BASE_MS * 2 ** retryRef.current) * (0.75 + Math.random() * 0.5);
      retryRef.current += 1;
      window.setTimeout(connect, delay);
    };

    connect();

    const staleTimer = window.setInterval(() => {
      if (lastFrameAtRef.current !== null && Date.now() - lastFrameAtRef.current > STALE_THRESHOLD_MS) {
        setStale(true);
      }
    }, 1_000);

    return () => {
      closedByUsRef.current = true;
      socketRef.current?.close();
      window.clearInterval(staleTimer);
    };
  }, []);

  return { workers, degraded, connected, stale };
}
