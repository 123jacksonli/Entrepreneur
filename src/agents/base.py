"""Base class for all agents in the pipeline."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from src.types import AgentLogEntry, AgentStatus

logger = logging.getLogger(__name__)


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


@dataclass
class BaseAgent(ABC):
    id: str = ""
    name: str = ""
    run_id: str = ""
    event_callback: Callable[[dict], None] | None = None

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent and return its result."""
        ...

    def log(self, message: str, level: str = "info") -> AgentLogEntry:
        from datetime import datetime, timezone

        entry: AgentLogEntry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,  # type: ignore[assignment]
            "message": message,
        }

        if self.event_callback and self.run_id:
            event = {
                "type": "agent-log",
                "run_id": self.run_id,
                "agent_id": self.id,
                "payload": dict(entry),
            }
            try:
                asyncio.get_running_loop()
                asyncio.create_task(self._emit_async(event))
            except RuntimeError:
                # No running loop; skip real-time emission.
                pass

        return entry

    async def _emit_async(self, event: dict) -> None:
        if self.event_callback:
            self.event_callback(event)
