import { AGENTS, EDGES } from "@/lib/agents";

describe("AGENTS config", () => {
  it("contains 8 agents", () => {
    expect(AGENTS).toHaveLength(8);
  });

  it("contains 8 edges including the plan → idea-generation loop", () => {
    expect(EDGES).toHaveLength(8);
    for (const edge of EDGES) {
      expect(AGENTS.find((a) => a.id === edge.source)).toBeDefined();
      expect(AGENTS.find((a) => a.id === edge.target)).toBeDefined();
    }
    expect(EDGES.some((e) => e.source === "plan" && e.target === "idea-generation")).toBe(true);
  });
});
