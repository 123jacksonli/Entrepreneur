import { RunRecord } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function startRun(idea: string): Promise<RunRecord> {
  const res = await fetch(`${API_BASE}/runs?idea=${encodeURIComponent(idea)}`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Failed to start run: ${res.statusText}`);
  }
  return res.json();
}

export async function stopRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/runs/${runId}/stop`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Failed to stop run: ${res.statusText}`);
  }
}

export async function fetchRuns(): Promise<RunRecord[]> {
  const res = await fetch(`${API_BASE}/runs`);
  if (!res.ok) {
    throw new Error(`Failed to fetch runs: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRun(id: string): Promise<RunRecord> {
  const res = await fetch(`${API_BASE}/runs/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch run: ${res.statusText}`);
  }
  return res.json();
}

// Local-storage helpers used by the mock orchestrator and history fallback.
export async function loadLocalRuns(): Promise<RunRecord[]> {
  if (typeof window === "undefined") return [];
  return JSON.parse(localStorage.getItem("runs") || "[]");
}

export async function saveLocalRun(run: RunRecord): Promise<void> {
  if (typeof window === "undefined") return;
  const runs = await loadLocalRuns();
  runs.unshift(run);
  localStorage.setItem("runs", JSON.stringify(runs));
}
