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

    async def start_run(self, run_id: str, idea: str) -> None:
        """Start and drive a pipeline run autonomously."""
        self.state.create_run(run_id, idea, "running", "idea-generation")
        await self._emit(PipelineEvent(type="run-started", run_id=run_id))

        # Autonomous loop: Idea Generation → Research → Plan until Plan approves or stops.
        idea_iterations = 0
        plan_decision = "iterate"
        while idea_iterations < self.config.MAX_IDEA_ITERATIONS:
            idea_iterations += 1
            await self._run_agent(run_id, "idea-generation", idea)
            await self._run_agent(run_id, "research", idea)
            plan_result = await self._run_agent(run_id, "plan", idea)
            plan_decision = plan_result.metadata.get("decision", "approve")

            if plan_decision == "stop":
                self.state.update_run(run_id, "stopped", "plan")
                await self._emit(
                    PipelineEvent(type="run-stopped", run_id=run_id, agent_id="plan")
                )
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
            self.state.update_run(run_id, "failed", "plan")
            await self._emit(
                PipelineEvent(
                    type="run-failed",
                    run_id=run_id,
                    agent_id="plan",
                    payload={"reason": "max_idea_iterations_exceeded"},
                )
            )
            return

        # Run the remaining stages.
        await self._run_agent(run_id, "execution-plan", idea)
        await self._run_agent(run_id, "architecture", idea)
        await self._run_agent(run_id, "execution", idea)
        await self._run_agent(run_id, "test", idea)

        # QA rejections loop back to Execution Agent up to MAX_QA_ITERATIONS.
        qa_iterations = 0
        qa_verdict = "reject"
        while qa_iterations < self.config.MAX_QA_ITERATIONS:
            qa_iterations += 1
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
            await self._run_agent(run_id, "execution", idea)
            await self._run_agent(run_id, "test", idea)
        else:
            self.state.update_run(run_id, "failed", "qa")
            await self._emit(
                PipelineEvent(
                    type="run-failed",
                    run_id=run_id,
                    agent_id="qa",
                    payload={"reason": "max_qa_iterations_exceeded"},
                )
            )
            return

        self.state.update_run(run_id, "completed", "qa")
        await self._emit(
            PipelineEvent(type="run-completed", run_id=run_id, agent_id="qa")
        )

    async def _run_agent(self, run_id: str, agent_id: str, idea: str) -> AgentResult:
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
            agent = agent_cls()
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

    async def _emit(self, event: PipelineEvent) -> None:
        if self.event_callback:
            self.event_callback(event)

    async def event_stream(self, run_id: str) -> AsyncGenerator[str, None]:
        """Yield SSE formatted events. Placeholder implementation."""
        yield f"data: {{\"type\": \"connected\", \"run_id\": \"{run_id}\"}}\n\n"
