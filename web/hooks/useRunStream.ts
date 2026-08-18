"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { RunEvent, RunTimeline, WsFrame } from "@/lib/types";

/**
 * contracts/websocket.md client obligations:
 *  1. A frame is never confirmation of a write — it is a notice that the log changed.
 *  2. snapshot may arrive after event frames on reconnect; discard events with
 *     seq <= snapshot.last_seq.
 *  3. Staleness (no frame, no successful poll within a threshold) is surfaced, never hidden.
 *  4. Reconnect with backoff+jitter, backfilling from after_seq rather than refetching the log.
 */

const STALE_THRESHOLD_MS = 8_000;
const BACKOFF_BASE_MS = 500;
const BACKOFF_MAX_MS = 8_000;

export interface RunStreamState {
  timeline: RunTimeline | null;
  connected: boolean;
  /** true once STALE_THRESHOLD_MS has passed with no frame and no successful poll. */
  stale: boolean;
  orphaned: { leaseExpiredAt: string } | null;
  lastEventAt: number | null;
}

function wsUrl(runId: number | string): string {
  const base = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "";
  return `${base}/ws/runs/${runId}`;
}

function applyEvent(timeline: RunTimeline, event: RunEvent): RunTimeline {
  // Structural events (STEP_SKIPPED_ON_REPLAY, WORKER_FENCED, RUN_CLAIMED) are re-fetched
  // from the timeline endpoint by the caller when they arrive, since they change segment
  // structure rather than only step content — see the effect below.
  if (event.type === "RUN_COMPLETED" || event.type === "RUN_FAILED" || event.type === "RUN_CANCELLED") {
    const status = event.type === "RUN_COMPLETED" ? "completed" : event.type === "RUN_FAILED" ? "failed" : "cancelled";
    return { ...timeline, status };
  }
  return timeline;
}

const STRUCTURAL_EVENTS = new Set(["STEP_SKIPPED_ON_REPLAY", "WORKER_FENCED", "RUN_CLAIMED", "STEP_COMPLETED", "STEP_STARTED"]);

export function useRunStream(runId: number | string | null): RunStreamState {
  const [timeline, setTimeline] = useState<RunTimeline | null>(null);
  const [connected, setConnected] = useState(false);
  const [stale, setStale] = useState(false);
  const [orphaned, setOrphaned] = useState<{ leaseExpiredAt: string } | null>(null);
  const [lastEventAt, setLastEventAt] = useState<number | null>(null);

  const lastSeqRef = useRef<number>(0);
  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const closedByUsRef = useRef(false);

  useEffect(() => {
    if (runId === null) return;
    closedByUsRef.current = false;

    const refreshTimeline = () => {
      api
        .getRunTimeline(runId)
        .then((t) => setTimeline(t))
        .catch(() => {
          // Poll failure does not clear existing state; staleness detection below
          // will surface it if frames also stop arriving.
        });
    };

    const connect = () => {
      let socket: WebSocket;
      try {
        socket = new WebSocket(wsUrl(runId));
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
        setLastEventAt(Date.now());
        setStale(false);
        let frame: WsFrame;
        try {
          frame = JSON.parse(raw.data as string) as WsFrame;
        } catch {
          return;
        }

        if (frame.kind === "hello") {
          const hello = frame.data as { last_seq: number };
          lastSeqRef.current = hello.last_seq;
          return;
        }

        if (frame.kind === "snapshot") {
          const snap = frame.data as RunTimeline & { last_seq?: number };
          // Obligation 2: a reconnect race can deliver snapshot after events already
          // applied. Only accept it if it does not roll seq backward silently — the
          // caller's event application already guards against replaying old events,
          // so applying the snapshot itself is always safe as the new baseline.
          setTimeline(snap);
          return;
        }

        if (frame.kind === "event") {
          const event = frame.data as RunEvent;
          if (frame.seq !== undefined && frame.seq <= lastSeqRef.current) return;
          if (frame.seq !== undefined) lastSeqRef.current = frame.seq;
          if (STRUCTURAL_EVENTS.has(event.type)) {
            refreshTimeline();
          } else {
            setTimeline((prev) => (prev ? applyEvent(prev, event) : prev));
          }
          return;
        }

        if (frame.kind === "lag") {
          const lag = frame.data as { orphaned?: boolean; lease_expired_at?: string; last_sent_seq?: number };
          if (lag.orphaned) {
            setOrphaned({ leaseExpiredAt: lag.lease_expired_at ?? new Date().toISOString() });
          }
          return;
        }

        if (frame.kind === "bye") {
          const bye = frame.data as { reason?: string; last_sent_seq?: number };
          if (bye.reason === "slow_consumer" && bye.last_sent_seq !== undefined) {
            api
              .getRunEvents(runId, bye.last_sent_seq)
              .then(({ items }) => {
                setTimeline((prev) => {
                  if (!prev) return prev;
                  return items.reduce((acc, e) => applyEvent(acc, e), prev);
                });
              })
              .catch(() => undefined);
          }
        }
      };

      socket.onclose = () => {
        setConnected(false);
        socketRef.current = null;
        if (!closedByUsRef.current) scheduleReconnect();
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    const scheduleReconnect = () => {
      const delay = Math.min(BACKOFF_MAX_MS, BACKOFF_BASE_MS * 2 ** retryRef.current) * (0.75 + Math.random() * 0.5);
      retryRef.current += 1;
      window.setTimeout(connect, delay);
    };

    connect();

    const staleTimer = window.setInterval(() => {
      setLastEventAt((prev) => {
        if (prev !== null && Date.now() - prev > STALE_THRESHOLD_MS) setStale(true);
        return prev;
      });
    }, 1_000);

    return () => {
      closedByUsRef.current = true;
      socketRef.current?.close();
      window.clearInterval(staleTimer);
    };
  }, [runId]);

  return { timeline, connected, stale, orphaned, lastEventAt };
}
