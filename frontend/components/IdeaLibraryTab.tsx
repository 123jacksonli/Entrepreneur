"use client";

import useSWR from "swr";
import { fetchRuns } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { RunRecord } from "@/types";
import { AgentStatusBadge } from "./AgentStatusBadge";

interface Props {
  filter: "approved" | "disapproved";
}

export function IdeaLibraryTab({ filter }: Props) {
  const { data: runs, error } = useSWR<RunRecord[]>("runs", fetchRuns, {
    refreshInterval: 5000,
  });
  const selectRun = useAppStore((s) => s.selectRun);
  const runsList = runs || [];

  const filtered = runsList.filter((run) => {
    if (filter === "approved") return run.status === "completed";
    return run.status === "stopped" || run.status === "failed";
  });

  const title = filter === "approved" ? "Approved Ideas" : "Disapproved Ideas";
  const emptyText =
    filter === "approved"
      ? "No approved ideas yet. Approved ideas appear here after QA accepts them."
      : "No disapproved ideas yet. Ideas that are stopped or fail QA appear here.";

  if (error) return <div className="p-4 text-red-500">Failed to load ideas.</div>;

  return (
    <div className="h-full overflow-auto p-4 space-y-3">
      <h2 className="text-lg font-semibold">{title}</h2>
      {filtered.length === 0 && <p className="text-gray-400">{emptyText}</p>}
      {filtered.map((run) => (
        <button
          key={run.id}
          onClick={() => selectRun(run.id)}
          className="w-full text-left border rounded-lg p-4 bg-white hover:bg-gray-50 transition"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm text-gray-500">{run.id}</span>
            <AgentStatusBadge status={run.status} />
          </div>
          <div className="text-sm text-gray-700 mt-1 font-medium">{run.idea}</div>
          <div className="text-sm text-gray-600 mt-1">
            Started: {new Date(run.created_at).toLocaleString()}
          </div>
          {run.completed_at && (
            <div className="text-sm text-gray-600">
              Completed: {new Date(run.completed_at).toLocaleString()}
            </div>
          )}
        </button>
      ))}
    </div>
  );
}
