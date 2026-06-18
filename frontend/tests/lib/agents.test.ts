import { AGENTS, EDGES } from "@/lib/agents";

describe("AGENTS config", () => {
  it("contains 9 agents", () => {
    expect(AGENTS).toHaveLength(9);
  });

  it("contains 9 edges including the plan → idea-generation loop", () => {
    expect(EDGES).toHaveLength(9);
    for (const edge of EDGES) {
      expect(AGENTS.find((a) => a.id === edge.source)).toBeDefined();
      expect(AGENTS.find((a) => a.id === edge.target)).toBeDefined();
    }
    expect(EDGES.some((e) => e.source === "plan" && e.target === "idea-generation")).toBe(true);
  });
});
