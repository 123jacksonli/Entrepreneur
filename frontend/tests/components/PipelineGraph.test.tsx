import { render, screen } from "@testing-library/react";
import { PipelineGraph } from "@/components/PipelineGraph";
import { useAppStore } from "@/lib/store";
import { AGENTS } from "@/lib/agents";

jest.mock("@xyflow/react", () => ({
  ReactFlow: ({ nodes, nodeTypes }: { nodes: any[]; nodeTypes: Record<string, React.ComponentType<any>> }) => {
    const NodeComponent = nodeTypes.agent;
    return (
      <div data-testid="react-flow">
        {nodes.map((node) => (
          <NodeComponent key={node.id} data={node.data} />
        ))}
      </div>
    );
  },
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
  useNodesState: (nodes: any[]) => [nodes, jest.fn()],
  useEdgesState: (edges: any[]) => [edges, jest.fn()],
}));

jest.mock("@/components/AgentNode", () => ({
  AgentNode: ({ data }: { data: { name: string } }) => <div>{data.name}</div>,
}));

describe("PipelineGraph", () => {
  beforeEach(() => {
    useAppStore.setState({ agents: AGENTS });
  });

  it("renders agent nodes", () => {
    render(<PipelineGraph />);
    expect(screen.getByText("Research Agent")).toBeInTheDocument();
    expect(screen.getByText("QA Agent")).toBeInTheDocument();
    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
  });
});
