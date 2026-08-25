import React, { createContext, useContext, useState, ReactNode } from "react";
import type {
  Health,
  RunTimeline,
  RunListItem,
  ChaosReport,
  ToolDescriptor,
  Worker,
  RunEvent,
} from "../lib/types";
import {
  DEMO_HEALTH,
  DEMO_WORKERS,
  DEMO_RUN_TIMELINE_CRASHED,
  DEMO_RUNS_LIST,
  DEMO_CHAOS_REPORT,
  DEMO_TOOLS,
  DEMO_EVENTS,
} from "../lib/demo-data";

export type DemoStateStage = "normal" | "crashed" | "recovered";
export type DemoTab = "dashboard" | "timeline" | "chaos" | "logs";

interface DemoContextType {
  stage: DemoStateStage;
  activeTab: DemoTab;
  setActiveTab: (tab: DemoTab) => void;
  health: Health;
  workers: Worker[];
  timeline: RunTimeline;
  runs: RunListItem[];
  chaosReport: ChaosReport;
  tools: ToolDescriptor[];
  events: RunEvent[];
  isSimulating: boolean;
  killWorker: (workerId: string) => Promise<void>;
  triggerRecovery: () => Promise<void>;
  resetDemoState: () => void;
}

const DemoContext = createContext<DemoContextType | null>(null);

export const DemoProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [stage, setStage] = useState<DemoStateStage>("normal");
  const [activeTab, setActiveTab] = useState<DemoTab>("timeline");
  const [isSimulating, setIsSimulating] = useState(false);

  // Derive dynamic state based on current stage
  const currentTimeline: RunTimeline = {
    ...DEMO_RUN_TIMELINE_CRASHED,
    segments:
      stage === "normal"
        ? [DEMO_RUN_TIMELINE_CRASHED.segments[0]]
        : DEMO_RUN_TIMELINE_CRASHED.segments,
    fencing_events: stage === "normal" ? [] : DEMO_RUN_TIMELINE_CRASHED.fencing_events,
    summary: {
      ...DEMO_RUN_TIMELINE_CRASHED.summary,
      handoff_count: stage === "normal" ? 0 : 1,
      recovery_seconds: stage === "normal" ? null : 3.1,
    },
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
    setStage("normal");
    setActiveTab("timeline");
  };

  return (
    <DemoContext.Provider
      value={{
        stage,
        activeTab,
        setActiveTab,
        health: DEMO_HEALTH,
        workers: DEMO_WORKERS,
        timeline: currentTimeline,
        runs: DEMO_RUNS_LIST,
        chaosReport: DEMO_CHAOS_REPORT,
        tools: DEMO_TOOLS,
        events: DEMO_EVENTS,
        isSimulating,
        killWorker,
        triggerRecovery,
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
