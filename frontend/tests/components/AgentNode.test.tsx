import { render, screen } from "@testing-library/react";
import { AgentNode } from "@/components/AgentNode";
import { Agent } from "@/types";

jest.mock("@xyflow/react", () => ({
  Handle: ({ type }: { type: string }) => <div data-testid={`handle-${type}`} />,
  Position: { Top: "top", Bottom: "bottom" },
}));

const mockAgent: Agent = {
  id: "research",
  name: "Research Agent",
  description: "Gathers data",
  status: "running",
  outputs: [],
  logs: [],
};

describe("AgentNode", () => {
  it("renders agent name and status", () => {
    render(<AgentNode data={mockAgent} />);
    expect(screen.getByText("Research Agent")).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
  });
});
