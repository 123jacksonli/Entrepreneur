"""Pipeline orchestrator for the autonomous 8-agent startup builder workflow."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable

from src.agents import AGENTS
from src.agents.base import AgentContext, AgentResult
from src.artifacts import ArtifactManager, ARTIFACT_PATHS
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
        config: Config | None = None,
        artifact_manager: ArtifactManager | None = None,
    ) -> None:
        self.state = state_store or StateStore()
        self.event_callback = event_callback
        self.config = config or Config()
        self.artifacts = artifact_manager or ArtifactManager()

        self._run_lock = asyncio.Lock()
        self._stop_flags: set[str] = set()
        self._subscribers: dict[str, list[asyncio.Queue[PipelineEvent]]] = {}

    async def start_run(self, run_id: str, idea: str) -> None:
        """Start and drive a pipeline run autonomously.

        Runs are serialized so only one pipeline is active at a time. A stop
        request lets the currently active agent finish, then exits cleanly.
        """
        async with self._run_lock:
            await self._run_pipeline(run_id, idea)

    async def _run_pipeline(self, run_id: str, idea: str) -> None:
        self.state.create_run(run_id, idea, "running", "idea-generation")
        self._clear_stop(run_id)
        await self._emit(PipelineEvent(type="run-started", run_id=run_id))

        # Autonomous loop: Idea Generation → Research → Plan until Plan approves or stops.
        idea_iterations = 0
        plan_decision = "iterate"
        while idea_iterations < self.config.MAX_IDEA_ITERATIONS:
            if self._should_stop(run_id):
                await self._finish_run(run_id, "stopped", "plan")
                return

            idea_iterations += 1
            await self._run_agent(run_id, "idea-generation", idea)
            await self._run_agent(run_id, "research", idea)
            plan_result = await self._run_agent(run_id, "plan", idea)
            plan_decision = plan_result.metadata.get("decision", "approve")

            if plan_decision == "stop":
                await self._finish_run(run_id, "stopped", "plan")
                return

            if plan_decision == "iterate":
                await self._emit(
                    PipelineEvent(
                        type="loop-iteration",
                        run_id=run_id,
                        agent_id="plan",
                        payload={"next": "idea-generation", "iteration": idea_iterations},
                    )
                )
                continue

            # plan_decision == "approve"
            break
        else:
            # Exceeded max iterations without approval.
            await self._finish_run(run_id, "failed", "plan")
            return

        # Run the remaining stages.
        await self._run_agent(run_id, "execution-plan", idea)
        await self._run_agent(run_id, "architecture", idea)

        # QA rejections loop back to Execution Agent up to MAX_QA_ITERATIONS.
        qa_iterations = 0
        qa_verdict = "reject"
        while qa_iterations < self.config.MAX_QA_ITERATIONS:
            if self._should_stop(run_id):
                await self._finish_run(run_id, "stopped", "qa")
                return

            qa_iterations += 1
            await self._run_agent(run_id, "execution", idea)
            await self._run_agent(run_id, "test", idea)
            qa_result = await self._run_agent(run_id, "qa", idea)
            qa_verdict = qa_result.metadata.get("verdict", "accept")
            if qa_verdict in ("accept", "conditional accept"):
                break

            await self._emit(
                PipelineEvent(
                    type="loop-iteration",
                    run_id=run_id,
                    agent_id="qa",
                    payload={
                        "next": "execution",
                        "iteration": qa_iterations,
                        "verdict": qa_verdict,
                    },
                )
            )
        else:
            await self._finish_run(run_id, "failed", "qa")
            return

        await self._finish_run(run_id, "completed", "qa")

    def request_stop(self, run_id: str) -> None:
        """Request that the run stop after the current agent finishes."""
        self._stop_flags.add(run_id)

    def _should_stop(self, run_id: str) -> bool:
        return run_id in self._stop_flags

    def _clear_stop(self, run_id: str) -> None:
        self._stop_flags.discard(run_id)

    async def _finish_run(
        self, run_id: str, status: str, current_agent_id: str
    ) -> None:
        terminal = status in ("completed", "stopped", "failed")
        self.state.update_run(run_id, status, current_agent_id, completed=terminal)
        event_type = (
            "run-completed"
            if status == "completed"
            else "run-stopped"
            if status == "stopped"
            else "run-failed"
        )
        await self._emit(
            PipelineEvent(type=event_type, run_id=run_id, agent_id=current_agent_id)
        )
        self._cleanup_run(run_id)

    def _cleanup_run(self, run_id: str) -> None:
        self._subscribers.pop(run_id, None)
        self._stop_flags.discard(run_id)

    async def _run_agent(self, run_id: str, agent_id: str, idea: str) -> AgentResult:
        if self._should_stop(run_id):
            # Skip new agents once a stop has been requested.
            return AgentResult(status="idle")

        await self._emit(
            PipelineEvent(
                type="agent-start",
                run_id=run_id,
                agent_id=agent_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

        # Load prior artifacts so the agent has full context.
        context_artifacts = {
            stage: self.artifacts.read(stage) for stage in ARTIFACT_PATHS
        }
        context = AgentContext(run_id=run_id, idea=idea, artifacts=context_artifacts)

        agent_cls = AGENTS.get(agent_id)
        if agent_cls:
            agent = agent_cls(artifact_manager=ArtifactManager(run_id=run_id))
            agent.run_id = run_id
            agent.event_callback = lambda event: asyncio.create_task(
                self._emit(PipelineEvent(**event))
            )
            result = await agent.run(context)
        else:
            # Placeholder for agents that are not yet implemented.
            await asyncio.sleep(0.1)
            result = AgentResult(status="completed")

        self.state.update_run(run_id, "running", agent_id)
        await self._emit(
            PipelineEvent(
                type="agent-complete",
                run_id=run_id,
                agent_id=agent_id,
                status=result.status,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return result

    async def _emit(self, event: PipelineEvent | dict) -> None:
        if isinstance(event, dict):
            event = PipelineEvent(**event)
        if self.event_callback:
            self.event_callback(event)
        for queue in list(self._subscribers.get(event.run_id, [])):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def event_stream(self, run_id: str) -> AsyncGenerator[str, None]:
        """Yield SSE formatted events for a run."""
        queue: asyncio.Queue[PipelineEvent] = asyncio.Queue(maxsize=256)
        self._subscribers.setdefault(run_id, []).append(queue)

        try:
            # Send a connection ack.
            ack = PipelineEvent(type="connected", run_id=run_id)
            yield f"data: {self._event_to_json(ack)}\n\n"

            while True:
                event = await asyncio.wait_for(queue.get(), timeout=300.0)
                yield f"data: {self._event_to_json(event)}\n\n"
                if event.type in ("run-completed", "run-stopped", "run-failed"):
                    break
        except asyncio.TimeoutError:
            pass
        finally:
            self._subscribers.get(run_id, []).remove(queue)

    @staticmethod
    def _event_to_json(event: PipelineEvent) -> str:
        import json

        return json.dumps(
            {
                "type": event.type,
                "run_id": event.run_id,
                "agent_id": event.agent_id,
                "status": event.status,
                "timestamp": event.timestamp,
                "payload": event.payload,
            }
        )
