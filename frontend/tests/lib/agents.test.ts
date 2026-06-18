import { AGENTS, EDGES } from "@/lib/agents";

describe("AGENTS config", () => {
  it("contains 8 agents", () => {
    expect(AGENTS).toHaveLength(8);
  });

  it("contains 7 edges connecting consecutive agents", () => {
    expect(EDGES).toHaveLength(7);
    for (const edge of EDGES) {
      expect(AGENTS.find((a) => a.id === edge.source)).toBeDefined();
      expect(AGENTS.find((a) => a.id === edge.target)).toBeDefined();
    }
  });
});
