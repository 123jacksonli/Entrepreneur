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
