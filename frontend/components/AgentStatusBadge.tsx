import { AgentStatus } from "@/types";

const styles: Record<AgentStatus, string> = {
  idle: "bg-gray-200 text-gray-800",
  running: "bg-blue-500 text-white animate-pulse",
  completed: "bg-green-500 text-white",
  failed: "bg-red-500 text-white",
  waiting: "bg-yellow-300 text-yellow-900",
  stopped: "bg-orange-400 text-white",
};

interface Props {
  status: AgentStatus;
}

export function AgentStatusBadge({ status }: Props) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}
