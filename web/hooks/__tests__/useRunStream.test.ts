import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useRunStream } from "../useRunStream";
import { installMockWebSocket } from "./mockSocket";
import { referenceMock } from "@/components/run/mocks";

describe("useRunStream (contracts/websocket.md)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("applies hello then snapshot, exposing the timeline", async () => {
    const MockWs = installMockWebSocket();
    const { result } = renderHook(() => useRunStream(47));

    await waitFor(() => expect(MockWs.instances.length).toBe(1));
    const socket = MockWs.instances[0]!;
    act(() => socket.emitOpen());
    act(() => socket.emit({ kind: "hello", data: { run_id: 47, last_seq: 3, deployment_mode: "local" } }));
    act(() => socket.emit({ kind: "snapshot", data: referenceMock }));

    await waitFor(() => expect(result.current.timeline).not.toBeNull());
    expect(result.current.timeline?.id).toBe(47);
    expect(result.current.connected).toBe(true);
  });

  it("surfaces staleness when no frame arrives within the threshold", async () => {
    vi.useFakeTimers();
    const MockWs = installMockWebSocket();
    const { result } = renderHook(() => useRunStream(47));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    const socket = MockWs.instances[0]!;
    act(() => socket.emitOpen());
    act(() => socket.emit({ kind: "snapshot", data: referenceMock }));

    expect(result.current.stale).toBe(false);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(9_000);
    });

    expect(result.current.stale).toBe(true);
  });

  it("surfaces an orphan transition pushed via a lag frame", async () => {
    const MockWs = installMockWebSocket();
    const { result } = renderHook(() => useRunStream(47));
    await waitFor(() => expect(MockWs.instances.length).toBe(1));
    const socket = MockWs.instances[0]!;
    act(() => socket.emitOpen());
    act(() => socket.emit({ kind: "lag", data: { orphaned: true, lease_expired_at: "2026-08-18T15:00:30.000Z" } }));

    await waitFor(() => expect(result.current.orphaned).not.toBeNull());
    expect(result.current.orphaned?.leaseExpiredAt).toBe("2026-08-18T15:00:30.000Z");
  });
});
