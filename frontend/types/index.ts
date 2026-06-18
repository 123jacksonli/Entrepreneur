export type AgentStatus = "idle" | "running" | "completed" | "failed" | "waiting" | "stopped";

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
  idea: string;
  status: AgentStatus;
  current_agent_id?: string;
  created_at: string;
  completed_at?: string;
}

export interface PipelineEvent {
  type: string;
  run_id: string;
  agent_id?: string;
  status?: AgentStatus;
  timestamp?: string;
  payload?: Record<string, unknown>;
}
