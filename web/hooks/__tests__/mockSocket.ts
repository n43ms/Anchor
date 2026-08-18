import { vi } from "vitest";

export class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }

  send() {}

  close() {
    this.closed = true;
    this.onclose?.();
  }

  emitOpen() {
    this.onopen?.();
  }

  emit(frame: unknown) {
    this.onmessage?.({ data: JSON.stringify(frame) });
  }
}

export function installMockWebSocket() {
  MockWebSocket.instances = [];
  // @ts-expect-error -- test-only global override
  globalThis.WebSocket = MockWebSocket;
  return MockWebSocket;
}

export function fetchJsonOnce(body: unknown) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
    ok: true,
    status: 200,
    json: async () => body,
  } as Response);
}
