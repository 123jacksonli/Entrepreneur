import { create } from "zustand";
import { Agent, RunRecord } from "@/types";

interface AppState {
  agents: Agent[];
  selectedAgentId: string | null;
  runs: RunRecord[];
  activeRunId: string | null;
  setAgents: (agents: Agent[]) => void;
  updateAgent: (id: string, patch: Partial<Agent>) => void;
  selectAgent: (id: string | null) => void;
  setRuns: (runs: RunRecord[]) => void;
  addRun: (run: RunRecord) => void;
  setActiveRunId: (id: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  agents: [],
  selectedAgentId: null,
  runs: [],
  activeRunId: null,
  setAgents: (agents) => set({ agents }),
  updateAgent: (id, patch) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, ...patch } : a)),
    })),
  selectAgent: (id) => set({ selectedAgentId: id }),
  setRuns: (runs) => set({ runs }),
  addRun: (run) => set((state) => ({ runs: [run, ...state.runs] })),
  setActiveRunId: (id) => set({ activeRunId: id }),
}));
