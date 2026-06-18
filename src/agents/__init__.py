"""Agent implementations."""

from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.agents.execution import ExecutionAgent

AGENTS: dict[str, type[BaseAgent]] = {
    "execution": ExecutionAgent,
}

__all__ = [
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "ExecutionAgent",
    "AGENTS",
]
