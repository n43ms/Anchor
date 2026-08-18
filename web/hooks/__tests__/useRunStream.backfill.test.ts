import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useRunStream } from "../useRunStream";
import { installMockWebSocket, fetchJsonOnce } from "./mockSocket";
import { referenceMock } from "@/components/run/mocks";

describe("useRunStream backfill (contracts/websocket.md client obligations)", () => {
  afterEach(() => vi.restoreAllMocks());

  it("backfills via after_seq rather than refetching the whole log on a slow-consumer bye", async () => {
    const MockWs = installMockWebSocket();
    renderHook(() => useRunStream(47));
    await waitFor(() => expect(MockWs.instances.length).toBe(1));
    const socket = MockWs.instances[0]!;
    act(() => socket.emitOpen());
    act(() => socket.emit({ kind: "snapshot", data: referenceMock }));

    const fetchSpy = fetchJsonOnce({ run_id: 47, items: [], next_after_seq: null });
    act(() => socket.emit({ kind: "bye", data: { reason: "slow_consumer", last_sent_seq: 126 } }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const calledUrl = fetchSpy.mock.calls[0]?.[0] as string;
    expect(calledUrl).toContain("after_seq=126");
    expect(calledUrl).not.toMatch(/\/events\?(?!after_seq)/);
  });

  it("discards events with seq <= snapshot.last_seq (reconnect race)", async () => {
    const MockWs = installMockWebSocket();
    const { result } = renderHook(() => useRunStream(47));
    await waitFor(() => expect(MockWs.instances.length).toBe(1));
    const socket = MockWs.instances[0]!;
    act(() => socket.emitOpen());
    act(() => socket.emit({ kind: "hello", data: { run_id: 47, last_seq: 130, deployment_mode: "local" } }));
    act(() => socket.emit({ kind: "snapshot", data: referenceMock }));

    // An event at or below last_seq arriving after the snapshot (the reconnect
    // race) must not be re-applied — status must stay whatever the snapshot said.
    act(() =>
      socket.emit({
        kind: "event",
        seq: 130,
        data: { run_id: 47, seq: 130, type: "RUN_FAILED", payload: {}, epoch: 1, worker_id: "worker-a#1", step_index: null, created_at: "x" },
      }),
    );

    await waitFor(() => expect(result.current.timeline).not.toBeNull());
    expect(result.current.timeline?.status).toBe(referenceMock.status);
  });
});
