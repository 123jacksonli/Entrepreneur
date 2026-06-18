import { AGENTS, EDGES } from "@/lib/agents";

describe("AGENTS config", () => {
  it("contains 9 agents", () => {
    expect(AGENTS).toHaveLength(9);
  });

  it("contains 8 edges connecting consecutive agents", () => {
    expect(EDGES).toHaveLength(8);
    for (const edge of EDGES) {
      expect(AGENTS.find((a) => a.id === edge.source)).toBeDefined();
      expect(AGENTS.find((a) => a.id === edge.target)).toBeDefined();
    }
  });
});
