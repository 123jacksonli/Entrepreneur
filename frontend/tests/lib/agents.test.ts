import { AGENTS, EDGES } from "@/lib/agents";

describe("AGENTS config", () => {
  it("contains 8 agents", () => {
    expect(AGENTS).toHaveLength(8);
  });

  it("contains 9 edges including both feedback loops", () => {
    expect(EDGES).toHaveLength(9);
    for (const edge of EDGES) {
      expect(AGENTS.find((a) => a.id === edge.source)).toBeDefined();
      expect(AGENTS.find((a) => a.id === edge.target)).toBeDefined();
    }
    expect(EDGES.some((e) => e.source === "plan" && e.target === "idea-generation")).toBe(true);
    expect(EDGES.some((e) => e.source === "qa" && e.target === "execution")).toBe(true);
  });
});
