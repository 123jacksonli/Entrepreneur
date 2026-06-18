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
