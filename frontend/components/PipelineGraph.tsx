"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { AgentNode } from "./AgentNode";
import { useAppStore } from "@/lib/store";
import { EDGES } from "@/lib/agents";
import { Agent } from "@/types";

const nodeTypes = { agent: AgentNode };

function getNodeStyle(status: Agent["status"]) {
  switch (status) {
    case "running":
      return { borderColor: "#3b82f6", backgroundColor: "#eff6ff" };
    case "completed":
      return { borderColor: "#22c55e", backgroundColor: "#f0fdf4" };
    case "failed":
      return { borderColor: "#ef4444", backgroundColor: "#fef2f2" };
    case "stopped":
      return { borderColor: "#f59e0b", backgroundColor: "#fffbeb" };
    default:
      return { borderColor: "#e2e8f0", backgroundColor: "#ffffff" };
  }
}

export function PipelineGraph() {
  const agents = useAppStore((s) => s.agents);

  const nodes: Node[] = useMemo(
    () =>
      agents.map((agent, index) => ({
        id: agent.id,
        type: "agent",
        position: {
          x: index * 220,
          y: index % 2 === 0 ? 100 : 300,
        },
        data: agent as unknown as Record<string, unknown>,
        style: getNodeStyle(agent.status),
      })),
    [agents]
  );

  const edges: Edge[] = useMemo(
    () =>
      EDGES.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        animated: true,
        style: { stroke: "#94a3b8" },
        labelStyle: { fill: "#64748b", fontSize: 12 },
      })),
    []
  );

  return (
    <div className="flex-1 h-[600px] border rounded-lg overflow-hidden">
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView>
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
