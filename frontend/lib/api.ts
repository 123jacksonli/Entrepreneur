import { RunRecord } from "@/types";

export async function fetchRuns(): Promise<RunRecord[]> {
  // TODO: replace with real API call
  if (typeof window === "undefined") return [];
  return JSON.parse(localStorage.getItem("runs") || "[]");
}

export async function saveRun(run: RunRecord): Promise<void> {
  if (typeof window === "undefined") return;
  const runs = await fetchRuns();
  runs.unshift(run);
  localStorage.setItem("runs", JSON.stringify(runs));
}
