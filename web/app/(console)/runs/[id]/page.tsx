"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useRunStream } from "@/hooks/useRunStream";
import { RunDetail } from "@/components/run/RunDetail";
import { TimelineTrack } from "@/components/run/TimelineTrack";
import { api, ApiRequestError } from "@/lib/api";

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const { timeline, connected, stale } = useRunStream(params.id);
  const [killError, setKillError] = useState<string | null>(null);

  const handleKill = (workerId: string) => {
    setKillError(null);
    // The parent owns the API call and its error handling (component-contract.md) —
    // RunDetail never calls the endpoint itself.
    api.killWorker(workerId).catch((err: unknown) => {
      setKillError(err instanceof ApiRequestError ? err.message : "kill request failed");
    });
  };

  if (!timeline) {
    return <p className="text-sm text-ink-muted" data-testid="run-detail-loading">loading…</p>;
  }

  return (
    <div data-testid="run-detail-page">
      {!connected && (
        <p className="mb-3 text-xs text-status-warning" data-testid="run-detail-connection-warning">
          {stale ? "connection stale — showing last known state" : "reconnecting…"}
        </p>
      )}
      {killError && <p className="mb-3 text-xs text-status-critical">{killError}</p>}

      <RunDetail run={timeline} onKill={handleKill} />

      <div className="mt-6">
        <h2 className="mb-2 text-sm text-ink-secondary">timeline track</h2>
        <TimelineTrack segments={timeline.segments} fencingEvents={timeline.fencing_events} />
      </div>
    </div>
  );
}
