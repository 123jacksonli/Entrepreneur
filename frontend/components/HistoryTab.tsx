"use client";

import { useEffect } from "react";
import useSWR from "swr";
import { useAppStore } from "@/lib/store";
import { fetchRuns } from "@/lib/api";
import { RunRecord } from "@/types";
import { AgentStatusBadge } from "./AgentStatusBadge";

export function HistoryTab() {
  const { data: runs, error } = useSWR<RunRecord[]>("runs", fetchRuns);
  const storeRuns = useAppStore((s) => s.runs);
  const setRuns = useAppStore((s) => s.setRuns);

  useEffect(() => {
    if (runs && runs.length > 0) setRuns(runs);
  }, [runs, setRuns]);

  const displayedRuns = storeRuns.length > 0 ? storeRuns : runs || [];

  if (error) return <div className="p-4 text-red-500">Failed to load history.</div>;
  if (!runs && !storeRuns.length)
    return <div className="p-4 text-gray-400">Loading history...</div>;

  return (
    <div className="h-full overflow-auto p-4 space-y-3">
      <h2 className="text-lg font-semibold">Run History</h2>
      {displayedRuns.length === 0 && (
        <p className="text-gray-400">No runs yet. Run the pipeline to see history.</p>
      )}
      {displayedRuns.map((run) => (
        <div key={run.id} className="border rounded-lg p-4 bg-white">
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm text-gray-500">{run.id}</span>
            <AgentStatusBadge status={run.status} />
          </div>
          <div className="text-sm text-gray-600 mt-1">
            Started: {new Date(run.startedAt).toLocaleString()}
          </div>
          {run.completedAt && (
            <div className="text-sm text-gray-600">
              Completed: {new Date(run.completedAt).toLocaleString()}
            </div>
          )}
          <div className="mt-2 text-sm">
            <strong>Agents:</strong> {run.agents.map((a) => a.name).join(" → ")}
          </div>
        </div>
      ))}
    </div>
  );
}
