/**
 * Typed fetch client against contracts/openapi.yaml. No query library (D-31) — callers
 * own their own loading/error state via the hooks in web/hooks/.
 */
import type {
  AgentDescriptor,
  ChaosParams,
  ChaosReport,
  ChaosRun,
  Health,
  Metrics,
  Run,
  RunEvent,
  RunListItem,
  RunStatus,
  RunSubmission,
  RunTimeline,
  RuntimeConfig,
  ToolDescriptor,
  Worker,
} from "./types";

export type { RunSubmission } from "./types";

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    let message = `request failed: ${res.status}`;
    let code: string | undefined;
    try {
      const body = (await res.json()) as { error?: string; message?: string };
      message = body.message ?? message;
      code = body.error;
    } catch {
      // response body was not JSON — the status code is all we have
    }
    throw new ApiRequestError(message, res.status, code);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),

  listRuns: (params?: { status?: RunStatus[]; is_demo?: boolean; cursor?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    params?.status?.forEach((s) => qs.append("status", s));
    if (params?.is_demo !== undefined) qs.set("is_demo", String(params.is_demo));
    if (params?.cursor) qs.set("cursor", params.cursor);
    if (params?.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<{ items: RunListItem[]; next_cursor: string | null }>(`/api/runs${suffix}`);
  },

  submitRun: (body: RunSubmission) =>
    request<Run>("/api/runs", { method: "POST", body: JSON.stringify(body) }),

  getRun: (id: number | string) => request<Run>(`/api/runs/${id}`),

  getRunTimeline: (id: number | string) => request<RunTimeline>(`/api/runs/${id}/timeline`),

  getRunEvents: (id: number | string, afterSeq?: number) => {
    const qs = afterSeq !== undefined ? `?after_seq=${afterSeq}` : "";
    return request<{ run_id: number; items: RunEvent[]; next_after_seq: number | null }>(
      `/api/runs/${id}/events${qs}`,
    );
  },

  cancelRun: (id: number | string) => request<Run>(`/api/runs/${id}/cancel`, { method: "POST" }),

  resolveRun: (id: number | string, resolution: "mark_executed" | "mark_not_executed" | "retry", note?: string) =>
    request<Run>(`/api/runs/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ resolution, note }),
    }),

  resetDemoRuns: () => request<{ runs_deleted: number }>("/api/runs/demo/reset", { method: "POST" }),

  listWorkers: () => request<{ items: Worker[] }>("/api/workers"),

  killWorker: (id: string, graceful = false) =>
    request<{ ok: boolean }>(`/api/workers/${encodeURIComponent(id)}/kill`, {
      method: "POST",
      body: JSON.stringify({ graceful }),
    }),

  listAgents: () => request<{ items: AgentDescriptor[] }>("/api/agents"),

  listTools: () => request<{ items: ToolDescriptor[] }>("/api/tools"),

  getMetrics: () => request<Metrics>("/api/metrics"),

  getRuntimeConfig: () => request<RuntimeConfig>("/api/config"),

  updateRuntimeConfig: (values: Record<string, number>) =>
    request<RuntimeConfig>("/api/config", { method: "PATCH", body: JSON.stringify({ values }) }),

  startChaos: (params: ChaosParams) =>
    request<ChaosRun>("/api/chaos/start", { method: "POST", body: JSON.stringify(params) }),

  listChaosRuns: () => request<{ items: ChaosRun[] }>("/api/chaos"),

  getLatestChaosReport: () => request<ChaosReport>("/api/chaos/latest"),

  getChaosReport: (id: number | string) => request<ChaosReport>(`/api/chaos/${id}/report`),
};
