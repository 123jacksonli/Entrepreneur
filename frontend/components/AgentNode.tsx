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

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectAgent(data.id);
    }
  };

  return (
    <button
      type="button"
      className="min-w-[180px] rounded-lg border bg-white p-3 shadow-sm cursor-pointer hover:shadow-md transition text-left"
      onClick={() => selectAgent(data.id)}
      onKeyDown={handleKeyDown}
      aria-label={`Select ${data.name}, status ${data.status}`}
    >
      <Handle type="target" position={Position.Top} />
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold text-sm">{data.name}</h3>
        <AgentStatusBadge status={data.status} />
      </div>
      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{data.description}</p>
      <Handle type="source" position={Position.Bottom} />
    </button>
  );
}
