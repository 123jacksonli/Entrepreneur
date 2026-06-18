"""Base class for all agents in the pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.types import AgentLogEntry, AgentStatus


@dataclass
class AgentContext:
    run_id: str
    idea: str
    artifacts: dict[str, str] = field(default_factory=dict)


@dataclass
class AgentResult:
    status: AgentStatus
    outputs: list[str] = field(default_factory=list)
    logs: list[AgentLogEntry] = field(default_factory=list)
    artifact_text: str = ""
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):
    id: str = ""
    name: str = ""

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent and return its result."""
        ...

    def log(self, message: str, level: str = "info") -> AgentLogEntry:
        from datetime import datetime, timezone

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,  # type: ignore[assignment]
            "message": message,
        }
