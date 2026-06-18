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
    const baseAgents = AGENTS.map((a) => ({
      ...a,
      status: "idle" as const,
      logs: [],
      outputs: [],
    }));
    setAgents(baseAgents);

    const currentAgents = [...baseAgents];

    for await (const event of runPipeline(baseAgents)) {
      if (event.type === "agent-start") {
        const agent = currentAgents.find((a) => a.id === event.agentId)!;
        updateAgent(event.agentId, {
          status: "running",
          logs: [...agent.logs, event.log],
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
