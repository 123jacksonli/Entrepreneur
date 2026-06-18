"use client";

import useSWR from "swr";
import { fetchRun, fetchRunArtifacts } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { AgentStatusBadge } from "./AgentStatusBadge";

const STAGE_LABELS: Record<string, string> = {
  "idea-generation": "1. Idea Generation",
  research: "2. Research",
  plan: "3. Plan / Competitor Analysis",
  "execution-plan": "4. Execution Plan",
  architecture: "5. Architecture",
  execution: "6. Execution / Code",
  test: "7. Test Report",
  qa: "8. QA Suggestions",
};

export function IdeaDetailTab() {
  const selectedRunId = useAppStore((s) => s.selectedRunId);

  const { data: run } = useSWR(
    selectedRunId ? ["run", selectedRunId] : null,
    ([, id]) => fetchRun(id)
  );
  const { data: artifactData } = useSWR(
    selectedRunId ? ["artifacts", selectedRunId] : null,
    ([, id]) => fetchRunArtifacts(id)
  );

  if (!selectedRunId) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400 p-4">
        Select an idea from Approved Ideas or Disapproved Ideas to view details.
      </div>
    );
  }

  if (!run || !artifactData) {
    return <div className="p-4 text-gray-400">Loading idea details...</div>;
  }

  const artifacts = artifactData.artifacts;

  return (
    <div className="h-full overflow-auto p-4 space-y-4">
      <div className="border rounded-lg p-4 bg-white">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{run.idea}</h2>
          <AgentStatusBadge status={run.status} />
        </div>
        <div className="text-sm text-gray-600 mt-1">
          Run: <span className="font-mono">{run.id}</span>
        </div>
        {run.current_agent_id && (
          <div className="text-sm text-gray-600">
            Current / final agent: <code>{run.current_agent_id}</code>
          </div>
        )}
        <div className="text-sm text-gray-600">
          Started: {new Date(run.created_at).toLocaleString()}
        </div>
        {run.completed_at && (
          <div className="text-sm text-gray-600">
            Completed: {new Date(run.completed_at).toLocaleString()}
          </div>
        )}
      </div>

      {Object.entries(STAGE_LABELS).map(([stage, label]) => {
        const content = artifacts[stage];
        if (!content) return null;
        return (
          <div key={stage} className="border rounded-lg p-4 bg-white">
            <h3 className="font-semibold mb-2">{label}</h3>
            <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 p-3 rounded">
              {content}
            </pre>
          </div>
        );
      })}
    </div>
  );
}
