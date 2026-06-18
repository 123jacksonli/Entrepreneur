import { create } from "zustand";
import { Agent, AgentLogEntry, RunRecord } from "@/types";

interface AppState {
  agents: Agent[];
  selectedAgentId: string | null;
  runs: RunRecord[];
  activeRunId: string | null;
  selectedRunId: string | null;
  setAgents: (agents: Agent[]) => void;
  updateAgent: (id: string, patch: Partial<Agent>) => void;
  selectAgent: (id: string | null) => void;
  setRuns: (runs: RunRecord[]) => void;
  addRun: (run: RunRecord) => void;
  setActiveRunId: (id: string | null) => void;
  selectRun: (id: string | null) => void;
  addAgentLog: (id: string, log: AgentLogEntry) => void;
}

export const useAppStore = create<AppState>((set) => ({
  agents: [],
  selectedAgentId: null,
  runs: [],
  activeRunId: null,
  selectedRunId: null,
  setAgents: (agents) => set({ agents }),
  updateAgent: (id, patch) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, ...patch } : a)),
    })),
  selectAgent: (id) => set({ selectedAgentId: id }),
  setRuns: (runs) => set({ runs }),
  addRun: (run) => set((state) => ({ runs: [run, ...state.runs] })),
  setActiveRunId: (id) => set({ activeRunId: id }),
  selectRun: (id) => set({ selectedRunId: id }),
  addAgentLog: (id, log) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.id === id ? { ...a, logs: [...a.logs, log] } : a
      ),
    })),
}));
