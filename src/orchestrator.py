"""Pipeline orchestrator for the 8-agent startup builder workflow."""

import asyncio
from dataclasses import dataclass, field
from typing import AsyncGenerator, Callable

from src.agents.base import AgentResult
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
        event_callback: Callable[[PipelineEvent], None] | None = None,
    ) -> None:
        self.state = state_store or StateStore()
        self.event_callback = event_callback

    async def start_run(self, run_id: str, idea: str) -> None:
        """Start and drive a pipeline run."""
        self.state.create_run(run_id, idea, "running", "idea-generation")
        await self._emit(PipelineEvent(type="run-started", run_id=run_id))

        # Loop: Idea Generation → Research → Plan until Plan approves or stops.
        while True:
            await self._run_agent(run_id, "idea-generation", idea)
            await self._run_agent(run_id, "research", idea)
            await self._run_agent(run_id, "plan", idea)

            # TODO: Parse the Plan Agent artifact to determine decision.
            # For now, approve on the first iteration so the scaffold can continue.
            decision = "approve"

            if decision == "stop":
                self.state.update_run(run_id, "stopped", "plan")
                await self._emit(PipelineEvent(type="run-stopped", run_id=run_id, agent_id="plan"))
                return

            if decision == "iterate":
                await self._emit(
                    PipelineEvent(
                        type="loop-iteration",
                        run_id=run_id,
                        agent_id="plan",
                        payload={"next": "idea-generation"},
                    )
                )
                continue

            # decision == "approve"
            break

        # TODO: implement Execution Plan, Architecture, Execution, Test, QA.
        self.state.update_run(run_id, "waiting", "execution-plan")

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

    async def event_stream(self, run_id: str) -> AsyncGenerator[str, None]:
        """Yield SSE formatted events. Placeholder implementation."""
        yield f"data: {{\"type\": \"connected\", \"run_id\": \"{run_id}\"}}\n\n"
