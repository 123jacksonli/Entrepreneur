import { runPipeline } from "@/lib/mock-orchestrator";
import { AGENTS } from "@/lib/agents";

describe("runPipeline", () => {
  it("yields start and complete events for each agent", async () => {
    const events: any[] = [];
    for await (const event of runPipeline(AGENTS, 0)) {
      events.push(event);
    }
    expect(events.filter((e) => e.type === "agent-start")).toHaveLength(AGENTS.length);
    expect(events.filter((e) => e.type === "agent-complete")).toHaveLength(AGENTS.length);
    expect(events.some((e) => e.type === "run-complete")).toBe(true);
  });
});
