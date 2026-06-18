import { Agent, AgentLogEntry, AgentStatus, RunRecord } from "@/types";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export type PipelineEvent =
  | {
      type: "agent-start";
      agentId: string;
      log: AgentLogEntry;
    }
  | {
      type: "agent-complete";
      agentId: string;
      status: AgentStatus;
      outputs: string[];
      log: AgentLogEntry;
    }
  | {
      type: "run-complete";
      record: RunRecord;
    };

export async function* runPipeline(
  agents: Agent[],
  delayMs = 800
): AsyncGenerator<PipelineEvent> {
  const runId = `run-${Date.now()}`;
  const startedAt = new Date().toISOString();

  for (const agent of agents) {
    const timestamp = new Date().toISOString();
    yield {
      type: "agent-start" as const,
      agentId: agent.id,
      log: { timestamp, level: "info", message: `${agent.name} started` } as AgentLogEntry,
    };

    await sleep(delayMs);

    const completedLog: AgentLogEntry = {
      timestamp: new Date().toISOString(),
      level: "info",
      message: `${agent.name} completed`,
    };

    yield {
      type: "agent-complete" as const,
      agentId: agent.id,
      status: "completed" as AgentStatus,
      outputs: [`outputs/${agent.id}-report.md`],
      log: completedLog,
    };
  }

  const record: RunRecord = {
    id: runId,
    idea: "Mock pipeline run",
    status: "completed",
    created_at: startedAt,
    completed_at: new Date().toISOString(),
  };

  yield { type: "run-complete" as const, record };
}
