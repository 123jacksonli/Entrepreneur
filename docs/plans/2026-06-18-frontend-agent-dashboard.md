# Frontend Agent Dashboard Implementation Plan

> **For Kimi:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Build a web frontend that visualizes the Entrepreneur Agent Startup pipeline (all agents, their connections, and workflow state) and provides a separate history tab for past agent runs.

**Architecture:** A Next.js 14+ single-page dashboard with two main tabs: **Live Pipeline** (interactive graph of agents and status) and **History** (chronological list of past runs with per-agent logs). State is managed in a central store, and a mock orchestrator service simulates agent progress until the real backend is ready.

**Tech Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui, `@xyflow/react` (React Flow) for the workflow graph, Zustand for state, and SWR for data fetching.

---

## Project Layout

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── globals.css
│   └── providers.tsx
├── components/
│   ├── ui/                    # shadcn/ui components
│   ├── AgentNode.tsx
│   ├── AgentEdge.tsx
│   ├── PipelineGraph.tsx
│   ├── AgentStatusBadge.tsx
│   ├── AgentDetailPanel.tsx
│   ├── LivePipelineTab.tsx
│   └── HistoryTab.tsx
├── lib/
│   ├── agents.ts              # agent definitions + pipeline edges
│   ├── store.ts               # Zustand store
│   ├── mock-orchestrator.ts   # simulated backend
│   └── api.ts                 # SWR fetchers
├── types/
│   └── index.ts
├── tests/
│   ├── components/
│   │   ├── AgentNode.test.tsx
│   │   ├── PipelineGraph.test.tsx
│   │   └── HistoryTab.test.tsx
│   └── lib/
│       └── mock-orchestrator.test.ts
├── public/
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## Task 1: Initialize Next.js Frontend Project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.js`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/providers.tsx`

**Step 1: Scaffold project**

Run:
```bash
cd /Users/hoiman/Documents/GitHub/Entrepreneur
npx create-next-app@14 frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm
```

Expected: Next.js project created at `frontend/`.

**Step 2: Install dependencies**

Run:
```bash
cd frontend
npm install zustand swr @xyflow/react lucide-react
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event jest jest-environment-jsdom
```

Expected: Dependencies installed without errors.

**Step 3: Configure Tailwind and path aliases**

`frontend/tailwind.config.ts`:
```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
```

`frontend/tsconfig.json` already contains `"paths": { "@/*": ["./*"] }` from create-next-app.

**Step 4: Add global styles**

`frontend/app/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #__next {
  height: 100%;
}
```

**Step 5: Create root layout**

`frontend/app/layout.tsx`:
```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Entrepreneur Agent Startup",
  description: "Visualize and manage your agent-driven startup builder",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

**Step 6: Create providers wrapper**

`frontend/app/providers.tsx`:
```tsx
"use client";

import { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
```

**Step 7: Verify dev server starts**

Run:
```bash
cd frontend
npm run dev
```

Expected: Server starts on `http://localhost:3000`. Stop after verifying.

**Step 8: Commit**

```bash
git add frontend/
git commit -m "chore: initialize Next.js frontend project"
```

---

## Task 2: Define Types and Agent Configuration

**Files:**
- Create: `frontend/types/index.ts`
- Create: `frontend/lib/agents.ts`

**Step 1: Write types**

`frontend/types/index.ts`:
```typescript
export type AgentStatus = "idle" | "running" | "completed" | "failed" | "waiting";

export interface Agent {
  id: string;
  name: string;
  description: string;
  status: AgentStatus;
  outputs: string[];
  logs: AgentLogEntry[];
}

export interface AgentLogEntry {
  timestamp: string;
  level: "info" | "warn" | "error";
  message: string;
}

export interface PipelineEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface RunRecord {
  id: string;
  startedAt: string;
  completedAt?: string;
  status: AgentStatus;
  agents: Agent[];
}
```

**Step 2: Write agent definitions**

`frontend/lib/agents.ts`:
```typescript
import { Agent, PipelineEdge } from "@/types";

export const AGENTS: Agent[] = [
  {
    id: "research",
    name: "Research Agent",
    description: "Gathers market data and trends online.",
    status: "idle",
    outputs: [],
    logs: [],
  },
  {
    id: "plan",
    name: "Plan Agent",
    description: "Analyzes competitors and validates feasibility.",
    status: "idle",
    outputs: [],
    logs: [],
  },
  {
    id: "execution-plan",
    name: "Execution Plan Agent",
    description: "Builds milestones, tasks, and timelines.",
    status: "idle",
    outputs: [],
    logs: [],
  },
  {
    id: "architecture",
    name: "Architecture Agent",
    description: "Designs the technical blueprint.",
    status: "idle",
    outputs: [],
    logs: [],
  },
  {
    id: "human-in-loop",
    name: "Human in the Loop",
    description: "Mandatory approval checkpoint.",
    status: "idle",
    outputs: [],
    logs: [],
  },
  {
    id: "execution",
    name: "Execution Agent",
    description: "Writes code, config, tests, and docs.",
    status: "idle",
    outputs: [],
    logs: [],
  },
  {
    id: "test",
    name: "Test Agent",
    description: "Runs tests and reports bugs.",
    status: "idle",
    outputs: [],
    logs: [],
  },
  {
    id: "qa",
    name: "QA Agent",
    description: "Challenges output and gives verdict.",
    status: "idle",
    outputs: [],
    logs: [],
  },
];

export const EDGES: PipelineEdge[] = [
  { id: "e1", source: "research", target: "plan" },
  { id: "e2", source: "plan", target: "execution-plan" },
  { id: "e3", source: "execution-plan", target: "architecture" },
  { id: "e4", source: "architecture", target: "human-in-loop" },
  { id: "e5", source: "human-in-loop", target: "execution" },
  { id: "e6", source: "execution", target: "test" },
  { id: "e7", source: "test", target: "qa" },
];
```

**Step 3: Test configuration shape**

`frontend/tests/lib/agents.test.ts`:
```typescript
import { AGENTS, EDGES } from "@/lib/agents";

describe("AGENTS config", () => {
  it("contains 8 agents", () => {
    expect(AGENTS).toHaveLength(8);
  });

  it("contains 7 edges connecting consecutive agents", () => {
    expect(EDGES).toHaveLength(7);
    for (const edge of EDGES) {
      expect(AGENTS.find((a) => a.id === edge.source)).toBeDefined();
      expect(AGENTS.find((a) => a.id === edge.target)).toBeDefined();
    }
  });
});
```

**Step 4: Run test**

Run:
```bash
cd frontend
npx jest tests/lib/agents.test.ts
```

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: define agent types and pipeline configuration"
```

---

## Task 3: Build Zustand Store and Mock Orchestrator

**Files:**
- Create: `frontend/lib/store.ts`
- Create: `frontend/lib/mock-orchestrator.ts`
- Create: `frontend/lib/api.ts`

**Step 1: Create Zustand store**

`frontend/lib/store.ts`:
```typescript
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
      agents: state.agents.map((a) =>
        a.id === id ? { ...a, ...patch } : a
      ),
    })),
  selectAgent: (id) => set({ selectedAgentId: id }),
  setRuns: (runs) => set({ runs }),
  addRun: (run) => set((state) => ({ runs: [run, ...state.runs] })),
  setActiveRunId: (id) => set({ activeRunId: id }),
}));
```

**Step 2: Create mock orchestrator**

`frontend/lib/mock-orchestrator.ts`:
```typescript
import { Agent, AgentLogEntry, AgentStatus, RunRecord } from "@/types";

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function* runPipeline(agents: Agent[]) {
  const runId = `run-${Date.now()}`;
  const startedAt = new Date().toISOString();

  for (const agent of agents) {
    const timestamp = new Date().toISOString();
    yield {
      type: "agent-start" as const,
      agentId: agent.id,
      log: { timestamp, level: "info", message: `${agent.name} started` } as AgentLogEntry,
    };

    await delay(800);

    const completedLog: AgentLogEntry = {
      timestamp: new Date().toISOString(),
      level: "info",
      message: `${agent.name} completed`,
    };

    yield {
      type: "agent-complete" as const,
      agentId: agent.id,
      status: (agent.id === "qa" ? "completed" : "completed") as AgentStatus,
      outputs: [`outputs/${agent.id}-report.md`],
      log: completedLog,
    };
  }

  const record: RunRecord = {
    id: runId,
    startedAt,
    completedAt: new Date().toISOString(),
    status: "completed",
    agents: agents.map((a) => ({ ...a, status: "completed", logs: [], outputs: [] })),
  };

  yield { type: "run-complete" as const, record };
}
```

**Step 3: Create API fetchers**

`frontend/lib/api.ts`:
```typescript
import { RunRecord } from "@/types";

export async function fetchRuns(): Promise<RunRecord[]> {
  // TODO: replace with real API call
  return JSON.parse(localStorage.getItem("runs") || "[]");
}

export async function saveRun(run: RunRecord): Promise<void> {
  const runs = await fetchRuns();
  runs.unshift(run);
  localStorage.setItem("runs", JSON.stringify(runs));
}
```

**Step 4: Test mock orchestrator**

`frontend/tests/lib/mock-orchestrator.test.ts`:
```typescript
import { runPipeline } from "@/lib/mock-orchestrator";
import { AGENTS } from "@/lib/agents";

describe("runPipeline", () => {
  it("yields start and complete events for each agent", async () => {
    const events: any[] = [];
    for await (const event of runPipeline(AGENTS)) {
      events.push(event);
    }
    expect(events.filter((e) => e.type === "agent-start")).toHaveLength(AGENTS.length);
    expect(events.filter((e) => e.type === "agent-complete")).toHaveLength(AGENTS.length);
    expect(events.some((e) => e.type === "run-complete")).toBe(true);
  });
});
```

**Step 5: Run tests**

Run:
```bash
cd frontend
npx jest tests/lib/mock-orchestrator.test.ts tests/lib/agents.test.ts
```

Expected: PASS.

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add Zustand store and mock orchestrator"
```

---

## Task 4: Build Agent UI Components

**Files:**
- Create: `frontend/components/AgentStatusBadge.tsx`
- Create: `frontend/components/AgentNode.tsx`
- Create: `frontend/components/AgentDetailPanel.tsx`
- Create: `frontend/components/ui/card.tsx`

**Step 1: Create status badge**

`frontend/components/AgentStatusBadge.tsx`:
```tsx
import { AgentStatus } from "@/types";

const styles: Record<AgentStatus, string> = {
  idle: "bg-gray-200 text-gray-800",
  running: "bg-blue-500 text-white animate-pulse",
  completed: "bg-green-500 text-white",
  failed: "bg-red-500 text-white",
  waiting: "bg-yellow-300 text-yellow-900",
};

interface Props {
  status: AgentStatus;
}

export function AgentStatusBadge({ status }: Props) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}
```

**Step 2: Create agent node for React Flow**

`frontend/components/AgentNode.tsx`:
```tsx
"use client";

import { Handle, Position } from "@xyflow/react";
import { AgentStatusBadge } from "./AgentStatusBadge";
import { useAppStore } from "@/lib/store";
import { Agent } from "@/types";

interface AgentNodeProps {
  data: Agent;
}

export function AgentNode({ data }: AgentNodeProps) {
  const selectAgent = useAppStore((s) => s.selectAgent);

  return (
    <div
      className="min-w-[180px] rounded-lg border bg-white p-3 shadow-sm cursor-pointer hover:shadow-md transition"
      onClick={() => selectAgent(data.id)}
    >
      <Handle type="target" position={Position.Top} />
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold text-sm">{data.name}</h3>
        <AgentStatusBadge status={data.status} />
      </div>
      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{data.description}</p>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
```

**Step 3: Create detail panel**

`frontend/components/AgentDetailPanel.tsx`:
```tsx
"use client";

import { useAppStore } from "@/lib/store";
import { AgentStatusBadge } from "./AgentStatusBadge";

export function AgentDetailPanel() {
  const selectedAgentId = useAppStore((s) => s.selectedAgentId);
  const agents = useAppStore((s) => s.agents);
  const agent = agents.find((a) => a.id === selectedAgentId);

  if (!agent) {
    return (
      <div className="h-full p-4 text-gray-400 text-sm">
        Select an agent to view details.
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">{agent.name}</h2>
        <AgentStatusBadge status={agent.status} />
      </div>
      <p className="text-sm text-gray-600">{agent.description}</p>

      <div>
        <h3 className="text-sm font-semibold mb-1">Outputs</h3>
        <ul className="text-sm list-disc list-inside text-gray-700">
          {agent.outputs.length === 0 && <li className="text-gray-400">No outputs yet</li>}
          {agent.outputs.map((o, i) => (
            <li key={i}>{o}</li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="text-sm font-semibold mb-1">Logs</h3>
        <div className="space-y-1 text-xs">
          {agent.logs.length === 0 && <span className="text-gray-400">No logs yet</span>}
          {agent.logs.map((log, i) => (
            <div key={i} className="border-l-2 pl-2 border-gray-300">
              <span className="text-gray-400">{log.timestamp}</span>{" "}
              <span className="font-medium">[{log.level}]</span>{" "}
              {log.message}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**Step 4: Test AgentNode renders**

`frontend/tests/components/AgentNode.test.tsx`:
```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { AgentNode } from "@/components/AgentNode";
import { Agent } from "@/types";

const mockAgent: Agent = {
  id: "research",
  name: "Research Agent",
  description: "Gathers data",
  status: "running",
  outputs: [],
  logs: [],
};

describe("AgentNode", () => {
  it("renders agent name and status", () => {
    render(<AgentNode data={mockAgent} />);
    expect(screen.getByText("Research Agent")).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
  });
});
```

**Step 5: Run tests**

Run:
```bash
cd frontend
npx jest tests/components/AgentNode.test.tsx
```

Expected: PASS.

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add agent UI components"
```

---

## Task 5: Build Pipeline Graph Visualization

**Files:**
- Create: `frontend/components/PipelineGraph.tsx`
- Modify: `frontend/app/page.tsx`

**Step 1: Create pipeline graph**

`frontend/components/PipelineGraph.tsx`:
```tsx
"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { AgentNode } from "./AgentNode";
import { useAppStore } from "@/lib/store";
import { AGENTS, EDGES } from "@/lib/agents";

const nodeTypes = { agent: AgentNode };

export function PipelineGraph() {
  const agents = useAppStore((s) => s.agents);

  const initialNodes: Node[] = useMemo(
    () =>
      agents.map((agent, index) => ({
        id: agent.id,
        type: "agent",
        position: { x: index * 220, y: index % 2 === 0 ? 100 : 250 },
        data: agent,
      })),
    [agents]
  );

  const initialEdges: Edge[] = useMemo(
    () =>
      EDGES.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        animated: true,
        style: { stroke: "#94a3b8" },
      })),
    []
  );

  const [nodes] = useNodesState(initialNodes);
  const [edges] = useEdgesState(initialEdges);

  return (
    <div className="flex-1 h-[600px] border rounded-lg overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
```

**Step 2: Update main page**

`frontend/app/page.tsx`:
```tsx
"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PipelineGraph } from "@/components/PipelineGraph";
import { AgentDetailPanel } from "@/components/AgentDetailPanel";
import { HistoryTab } from "@/components/HistoryTab";
import { useAppStore } from "@/lib/store";
import { AGENTS } from "@/lib/agents";
import { runPipeline } from "@/lib/mock-orchestrator";
import { saveRun } from "@/lib/api";

export default function Home() {
  const { agents, setAgents, updateAgent, addRun } = useAppStore();
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    if (agents.length === 0) {
      setAgents(AGENTS);
    }
  }, [agents.length, setAgents]);

  const handleRun = async () => {
    setIsRunning(true);
    const baseAgents = AGENTS.map((a) => ({ ...a, status: "idle", logs: [], outputs: [] }));
    setAgents(baseAgents);

    const currentAgents = [...baseAgents];

    for await (const event of runPipeline(baseAgents)) {
      if (event.type === "agent-start") {
        updateAgent(event.agentId, {
          status: "running",
          logs: [...currentAgents.find((a) => a.id === event.agentId)!.logs, event.log],
        });
      }
      if (event.type === "agent-complete") {
        const agent = currentAgents.find((a) => a.id === event.agentId)!;
        updateAgent(event.agentId, {
          status: event.status,
          outputs: event.outputs,
          logs: [...agent.logs, event.log],
        });
      }
      if (event.type === "run-complete") {
        addRun(event.record);
        await saveRun(event.record);
      }
    }

    setIsRunning(false);
  };

  return (
    <main className="h-screen flex flex-col p-4 gap-4">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Entrepreneur Agent Startup</h1>
        <button
          onClick={handleRun}
          disabled={isRunning}
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          {isRunning ? "Running..." : "Run Pipeline"}
        </button>
      </header>

      <Tabs defaultValue="pipeline" className="flex-1 flex flex-col">
        <TabsList>
          <TabsTrigger value="pipeline">Live Pipeline</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="pipeline" className="flex-1 flex gap-4">
          <PipelineGraph />
          <aside className="w-80 border rounded-lg">
            <AgentDetailPanel />
          </aside>
        </TabsContent>

        <TabsContent value="history" className="flex-1">
          <HistoryTab />
        </TabsContent>
      </Tabs>
    </main>
  );
}
```

**Step 3: Add shadcn tabs**

Use the shadcn/ui CLI or manually create the tabs component. Since we did not init shadcn, create a lightweight custom tabs component.

`frontend/components/ui/tabs.tsx`:
```tsx
"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";

export const Tabs = TabsPrimitive.Root;
export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={`inline-flex h-10 items-center justify-center rounded-md bg-gray-100 p-1 text-gray-500 ${className}`}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={`inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-white transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm ${className}`}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

export const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={`mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 ${className}`}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;
```

Install Radix:
```bash
cd frontend
npm install @radix-ui/react-tabs
```

**Step 4: Test pipeline graph renders**

`frontend/tests/components/PipelineGraph.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { PipelineGraph } from "@/components/PipelineGraph";
import { useAppStore } from "@/lib/store";
import { AGENTS } from "@/lib/agents";

describe("PipelineGraph", () => {
  beforeEach(() => {
    useAppStore.setState({ agents: AGENTS });
  });

  it("renders agent nodes", () => {
    render(<PipelineGraph />);
    expect(screen.getByText("Research Agent")).toBeInTheDocument();
    expect(screen.getByText("QA Agent")).toBeInTheDocument();
  });
});
```

**Step 5: Run tests**

Run:
```bash
cd frontend
npx jest tests/components/PipelineGraph.test.tsx
```

Expected: PASS.

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add pipeline graph and main dashboard layout"
```

---

## Task 6: Build History Tab

**Files:**
- Create: `frontend/components/HistoryTab.tsx`
- Create: `frontend/components/ui/badge.tsx`

**Step 1: Create history tab**

`frontend/components/HistoryTab.tsx`:
```tsx
"use client";

import { useEffect } from "react";
import useSWR from "swr";
import { useAppStore } from "@/lib/store";
import { fetchRuns } from "@/lib/api";
import { RunRecord } from "@/types";
import { AgentStatusBadge } from "./AgentStatusBadge";

export function HistoryTab() {
  const { data: runs, error } = useSWR<RunRecord[]>("runs", fetchRuns);
  const storeRuns = useAppStore((s) => s.runs);
  const setRuns = useAppStore((s) => s.setRuns);

  useEffect(() => {
    if (runs) setRuns(runs);
  }, [runs, setRuns]);

  const displayedRuns = storeRuns.length > 0 ? storeRuns : runs || [];

  if (error) return <div className="p-4 text-red-500">Failed to load history.</div>;
  if (!runs && !storeRuns.length) return <div className="p-4 text-gray-400">Loading history...</div>;

  return (
    <div className="h-full overflow-auto p-4 space-y-3">
      <h2 className="text-lg font-semibold">Run History</h2>
      {displayedRuns.length === 0 && (
        <p className="text-gray-400">No runs yet. Run the pipeline to see history.</p>
      )}
      {displayedRuns.map((run) => (
        <div key={run.id} className="border rounded-lg p-4 bg-white">
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm text-gray-500">{run.id}</span>
            <AgentStatusBadge status={run.status} />
          </div>
          <div className="text-sm text-gray-600 mt-1">
            Started: {new Date(run.startedAt).toLocaleString()}
          </div>
          {run.completedAt && (
            <div className="text-sm text-gray-600">
              Completed: {new Date(run.completedAt).toLocaleString()}
            </div>
          )}
          <div className="mt-2 text-sm">
            <strong>Agents:</strong>{" "}
            {run.agents.map((a) => a.name).join(" → ")}
          </div>
        </div>
      ))}
    </div>
  );
}
```

**Step 2: Test history tab**

`frontend/tests/components/HistoryTab.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { HistoryTab } from "@/components/HistoryTab";
import { useAppStore } from "@/lib/store";
import { RunRecord } from "@/types";

const mockRun: RunRecord = {
  id: "run-1",
  startedAt: new Date().toISOString(),
  status: "completed",
  agents: [],
};

describe("HistoryTab", () => {
  beforeEach(() => {
    useAppStore.setState({ runs: [mockRun] });
  });

  it("renders run records", () => {
    render(<HistoryTab />);
    expect(screen.getByText("run-1")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
  });
});
```

**Step 3: Run tests**

Run:
```bash
cd frontend
npx jest tests/components/HistoryTab.test.tsx
```

Expected: PASS.

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: add history tab for past agent runs"
```

---

## Task 7: Jest Configuration and Final Verification

**Files:**
- Create: `frontend/jest.config.js`
- Create: `frontend/jest.setup.js`
- Modify: `frontend/tsconfig.json` if needed

**Step 1: Configure Jest**

`frontend/jest.config.js`:
```javascript
const nextJest = require("next/jest");

const createJestConfig = nextJest({
  dir: "./",
});

const customJestConfig = {
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  testEnvironment: "jest-environment-jsdom",
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
  },
};

module.exports = createJestConfig(customJestConfig);
```

`frontend/jest.setup.js`:
```javascript
import "@testing-library/jest-dom";
```

**Step 2: Run all tests**

Run:
```bash
cd frontend
npx jest
```

Expected: All tests PASS.

**Step 3: Run lint and build**

Run:
```bash
cd frontend
npm run lint
npm run build
```

Expected: No lint errors; static build succeeds.

**Step 4: Commit**

```bash
git add frontend/
git commit -m "chore: configure jest and verify frontend build"
```

---

## Task 8: Update AGENTS.md with Frontend Reference

**Files:**
- Modify: `AGENTS.md`

**Step 1: Add frontend section**

Append to `AGENTS.md`:

```markdown
## 7. Frontend Dashboard

A Next.js frontend visualizes the agent pipeline:

- **Live Pipeline tab** — interactive graph of all 8 agents, their statuses, and connections.
- **Agent detail panel** — click any agent to see outputs and logs.
- **History tab** — chronological list of past pipeline runs.

Code lives in `frontend/`. The frontend uses mock orchestration until the backend API is available.
```

**Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: document frontend dashboard in AGENTS.md"
```

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-06-18-frontend-agent-dashboard.md`.

**Two execution options:**

1. **Subagent-Driven (this session)** — I dispatch fresh subagents per task, review between tasks, fast iteration.
2. **Parallel Session (separate)** — Open a new session with `superpowers:executing-plans`, batch execution with checkpoints.

Which approach do you prefer?
