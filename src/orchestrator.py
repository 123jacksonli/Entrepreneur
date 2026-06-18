"""Pipeline orchestrator for the 8-agent startup builder workflow."""

import asyncio
from dataclasses import dataclass, field
from typing import AsyncGenerator, Callable

from src.agents.base import AgentResult
from src.checkpoint import CheckpointResult, HumanCheckpoint
from src.config import Config
from src.state import StateStore


@dataclass
class PipelineEvent:
    type: str
    run_id: str
    agent_id: str | None = None
    status: str | None = None
    timestamp: str | None = None
    payload: dict = field(default_factory=dict)


class Orchestrator:
    def __init__(
        self,
        state_store: StateStore | None = None,
        checkpoint: HumanCheckpoint | None = None,
        event_callback: Callable[[PipelineEvent], None] | None = None,
    ) -> None:
        self.state = state_store or StateStore()
        self.checkpoint = checkpoint or HumanCheckpoint()
        self.event_callback = event_callback

    async def start_run(self, run_id: str, idea: str) -> None:
        """Start and drive a pipeline run."""
        self.state.create_run(run_id, idea, "running", "idea-generation")
        await self._emit(PipelineEvent(type="run-started", run_id=run_id))

        # Placeholder: execute idea generation agent, then research agent.
        await self._run_agent(run_id, "idea-generation", idea)
        await self._run_agent(run_id, "research", idea)

        # TODO: implement remaining agents and checkpoint.
        self.state.update_run(run_id, "waiting", "plan")

    async def _run_agent(self, run_id: str, agent_id: str, idea: str) -> AgentResult:
        from datetime import datetime, timezone

        await self._emit(
            PipelineEvent(
                type="agent-start",
                run_id=run_id,
                agent_id=agent_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

        # TODO: instantiate and run actual agent.
        await asyncio.sleep(0.1)

        self.state.update_run(run_id, "running", agent_id)
        await self._emit(
            PipelineEvent(
                type="agent-complete",
                run_id=run_id,
                agent_id=agent_id,
                status="completed",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return AgentResult(status="completed")

    async def _emit(self, event: PipelineEvent) -> None:
        if self.event_callback:
            self.event_callback(event)

    async def approve_checkpoint(self, run_id: str, result: CheckpointResult) -> None:
        self.checkpoint.resolve(result)
        self.state.update_run(run_id, "running", "execution")
        await self._emit(
            PipelineEvent(type="checkpoint-resolved", run_id=run_id, payload={"decision": result.decision.value})
        )

    async def event_stream(self, run_id: str) -> AsyncGenerator[str, None]:
        """Yield SSE formatted events. Placeholder implementation."""
        yield f"data: {{\"type\": \"connected\", \"run_id\": \"{run_id}\"}}\n\n"
