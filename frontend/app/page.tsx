"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PipelineGraph } from "@/components/PipelineGraph";
import { AgentDetailPanel } from "@/components/AgentDetailPanel";
import { HistoryTab } from "@/components/HistoryTab";
import { IdeaLibraryTab } from "@/components/IdeaLibraryTab";
import { IdeaDetailTab } from "@/components/IdeaDetailTab";
import { useAppStore } from "@/lib/store";
import { AGENTS } from "@/lib/agents";
import { startRun, stopRun } from "@/lib/api";
import { useRunEvents } from "@/lib/sse";
import { AgentLogEntry, AgentStatus, PipelineEvent } from "@/types";

export default function Home() {
  const {
    agents,
    setAgents,
    updateAgent,
    addAgentLog,
    addRun,
    activeRunId,
    setActiveRunId,
  } = useAppStore();
  const [isRunning, setIsRunning] = useState(false);
  const [idea, setIdea] = useState(
    "Build a small startup that solves a common daily problem using AI."
  );

  useEffect(() => {
    if (agents.length === 0) {
      setAgents(
        AGENTS.map((a) => ({
          ...a,
          status: "idle" as AgentStatus,
          logs: [],
          outputs: [],
        }))
      );
    }
  }, [agents.length, setAgents]);

  const resetAgents = () => {
    setAgents(
      AGENTS.map((a) => ({
        ...a,
        status: "idle" as AgentStatus,
        logs: [],
        outputs: [],
      }))
    );
  };

  const handleEvent = (event: PipelineEvent) => {
    if (event.type === "agent-start" && event.agent_id) {
      updateAgent(event.agent_id, { status: "running" });
    }
    if (event.type === "agent-complete" && event.agent_id) {
      updateAgent(event.agent_id, { status: event.status ?? "completed" });
    }
    if (event.type === "agent-log" && event.agent_id && event.payload) {
      addAgentLog(event.agent_id, event.payload as unknown as AgentLogEntry);
    }
  };

  const handleComplete = () => {
    setIsRunning(false);
  };

  useRunEvents(activeRunId, handleEvent, handleComplete);

  const handleRun = async () => {
    resetAgents();
    setIsRunning(true);
    try {
      const run = await startRun(idea);
      setActiveRunId(run.id);
      addRun(run);
    } catch (error) {
      console.error("Failed to start run:", error);
      setIsRunning(false);
    }
  };

  const handleStop = async () => {
    if (!activeRunId) return;
    try {
      await stopRun(activeRunId);
    } catch (error) {
      console.error("Failed to stop run:", error);
    }
  };

  return (
    <main className="h-screen flex flex-col p-4 gap-4">
      <header className="flex items-center justify-between gap-4 flex-wrap">
        <h1 className="text-2xl font-bold">Entrepreneur Agent Startup</h1>
        <div className="flex items-center gap-2 flex-1 min-w-[16rem]">
          <input
            type="text"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="Describe your startup idea..."
            className="flex-1 px-3 py-2 border rounded text-sm"
            disabled={isRunning}
          />
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
          >
            {isRunning ? "Running..." : "Run Pipeline"}
          </button>
          <button
            onClick={handleStop}
            disabled={!isRunning}
            className="px-4 py-2 bg-red-600 text-white rounded disabled:opacity-50"
          >
            Stop
          </button>
        </div>
      </header>

      <Tabs defaultValue="pipeline" className="flex-1 flex flex-col">
        <TabsList>
          <TabsTrigger value="pipeline">Live Pipeline</TabsTrigger>
          <TabsTrigger value="approved">Approved Ideas</TabsTrigger>
          <TabsTrigger value="disapproved">Disapproved Ideas</TabsTrigger>
          <TabsTrigger value="detail">Idea Detail</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="pipeline" className="flex-1 flex gap-4">
          <PipelineGraph />
          <aside className="w-80 border rounded-lg">
            <AgentDetailPanel />
          </aside>
        </TabsContent>

        <TabsContent value="approved" className="flex-1">
          <IdeaLibraryTab filter="approved" />
        </TabsContent>

        <TabsContent value="disapproved" className="flex-1">
          <IdeaLibraryTab filter="disapproved" />
        </TabsContent>

        <TabsContent value="detail" className="flex-1">
          <IdeaDetailTab />
        </TabsContent>

        <TabsContent value="history" className="flex-1">
          <HistoryTab />
        </TabsContent>
      </Tabs>
    </main>
  );
}
