import React, { createContext, useContext, useState, ReactNode } from "react";
import type {
  Health,
  RunTimeline,
  RunListItem,
  ChaosReport,
  Worker,
  RunEvent,
} from "../lib/types";
import {
  DEMO_HEALTH,
  DEMO_WORKERS,
  DEMO_RUN_TIMELINE_CRASHED,
  DEMO_RUNS_LIST,
  DEMO_CHAOS_REPORT,
  DEMO_EVENTS,
} from "../lib/demo-data";

export type DemoStateStage = "normal" | "crashed" | "recovered";
export type DemoTab =
  | "overview-dashboard"
  | "runs-all"
  | "runs-needs-review"
  | "run-detail"
  | "workers-fleet"
  | "workers-deployments"
  | "chaos-console"
  | "chaos-history"
  | "tools-registry"
  | "tools-test-run"
  | "observability-metrics"
  | "observability-logs"
  | "settings-environment";

interface DemoContextType {
  stage: DemoStateStage;
  activeTab: DemoTab;
  setActiveTab: (tab: DemoTab) => void;
  selectedRunId: number;
  setSelectedRunId: (id: number) => void;
  isInspectorOpen: boolean;
  setIsInspectorOpen: (open: boolean) => void;
  health: Health;
  workers: Worker[];
  timeline: RunTimeline;
  runs: RunListItem[];
  chaosReport: ChaosReport;
  events: RunEvent[];
  isSimulating: boolean;
  killWorker: (workerId: string) => Promise<void>;
  triggerRecovery: () => Promise<void>;
  submitNewRun: (preset?: string) => Promise<void>;
  resetDemoState: () => void;
}

const DemoContext = createContext<DemoContextType | null>(null);

export const DemoProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [stage, setStage] = useState<DemoStateStage>("normal");
  const [activeTab, setActiveTab] = useState<DemoTab>("run-detail");
  const [selectedRunId, setSelectedRunId] = useState<number>(101);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [customRun, setCustomRun] = useState<RunTimeline | null>(null);

  const currentTimeline: RunTimeline = customRun || {
    ...DEMO_RUN_TIMELINE_CRASHED,
    segments: DEMO_RUN_TIMELINE_CRASHED.segments,
    fencing_events: DEMO_RUN_TIMELINE_CRASHED.fencing_events,
    summary: DEMO_RUN_TIMELINE_CRASHED.summary,
  };


  const submitNewRun = async (preset = "candidate_eval") => {
    setIsSimulating(true);
    await new Promise((r) => setTimeout(r, 300));
    const newId = Math.floor(100 + Math.random() * 900);
    const newRun: RunTimeline = {
      id: newId,
      display_id: `r${newId}`,
      agent_type: preset === "long_loop" ? "resumable_loop_agent" : "candidate_eval_agent",
      status: "running",
      started_at: new Date().toISOString(),
      step_count: 3,
      segments: [
        {
          worker_id: "worker-a#1",
          epoch: 1,
          claim_reason: "initial",
          started_at: new Date().toISOString(),
          ended_at: null,
          steps: [
            {
              step_index: 0,
              name: "initialize_eval_sandbox",
              status: "done",
              action_kind: "tool",
              started_at: new Date().toISOString(),
              completed_at: new Date().toISOString(),
              duration_ms: 600,
              idempotency_key: `r${newId}:s0:init`,
              idempotency_key_display: "a1b2c3d4",
              executed: true,
            },
            {
              step_index: 1,
              name: "compile_candidate_solution",
              status: "active",
              action_kind: "model",
              started_at: new Date().toISOString(),
              completed_at: null,
              duration_ms: null,
              idempotency_key: `r${newId}:s1:compile`,
              idempotency_key_display: "e5f6g7h8",
              executed: true,
            },
          ],
        },
      ],
      summary: { duplicate_side_effects: 0, handoff_count: 0, recovery_seconds: null },
    };

    setCustomRun(newRun);
    setSelectedRunId(newId);
    setStage("normal");
    setActiveTab("run-detail");
    setIsSimulating(false);
  };

  const killWorker = async (_workerId: string) => {
    setIsSimulating(true);
    await new Promise((r) => setTimeout(r, 300));
    setStage("crashed");
    setIsSimulating(false);
  };

  const triggerRecovery = async () => {
    setIsSimulating(true);
    await new Promise((r) => setTimeout(r, 400));
    setStage("recovered");
    setIsSimulating(false);
  };

  const resetDemoState = () => {
    setCustomRun(null);
    setStage("normal");
    setActiveTab("run-detail");
    setSelectedRunId(101);
  };

  return (
    <DemoContext.Provider
      value={{
        stage,
        activeTab,
        setActiveTab,
        selectedRunId,
        setSelectedRunId,
        isInspectorOpen,
        setIsInspectorOpen,
        health: DEMO_HEALTH,
        workers: DEMO_WORKERS,
        timeline: currentTimeline,
        runs: DEMO_RUNS_LIST,
        chaosReport: DEMO_CHAOS_REPORT,
        events: DEMO_EVENTS,
        isSimulating,
        killWorker,
        triggerRecovery,
        submitNewRun,
        resetDemoState,
      }}
    >
      {children}
    </DemoContext.Provider>
  );
};




export const useDemo = (): DemoContextType => {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error("useDemo must be used within a DemoProvider");
  }
  return context;
};
