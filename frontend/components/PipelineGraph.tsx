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
import { EDGES } from "@/lib/agents";

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
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView>
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
