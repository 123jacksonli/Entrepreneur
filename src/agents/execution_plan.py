"""Execution Plan Agent: converts the approved strategy into milestones and tasks."""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPlanAgent(BaseAgent):
    id: str = "execution-plan"
    name: str = "Execution Plan Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []
        plan_report = context.artifacts.get("plan", "")
        research_report = context.artifacts.get("research", "")

        user_prompt = f"""Plan report:
{plan_report}

Research report:
{research_report}

Write an execution plan for the approved idea."""

        system_prompt = (
            "You are the Execution Plan Agent. Convert the strategy into a concrete, "
            "actionable plan with these sections:\n"
            "1. Project Goal\n"
            "2. Milestones\n"
            "3. Task Breakdown\n"
            "4. Sequence / Timeline\n"
            "5. Resource Requirements\n"
            "6. Definition of Done\n"
            "7. Open Questions\n\n"
            "Do not write code or architecture."
        )

        fallback = f"""# Execution Plan

## Project Goal
Build a minimal viable product that validates the core idea quickly.

## Milestones
1. **MVP scaffold** — project setup, CI, and hello-world deployment.
2. **Core feature** — implement the single most important user-facing capability.
3. **Tests & docs** — unit tests, README, and runbook.
4. **QA & polish** — review, fix issues, and merge to main.

## Task Breakdown
- Milestone 1: repo setup, dependency management, basic health endpoint.
- Milestone 2: implement domain logic and API surface.
- Milestone 3: write tests and documentation.
- Milestone 4: run test suite, address QA feedback.

## Sequence / Timeline
1. Milestone 1 — small
2. Milestone 2 — medium
3. Milestone 3 — small
4. Milestone 4 — small

## Resource Requirements
- Python + FastAPI backend
- Next.js frontend
- SQLite for local state
- LLM API key

## Definition of Done
Each milestone has passing tests and a committed, pushed run branch.

## Open Questions
- Exact UI/UX details for the first milestone.
"""

        content = call_llm(self.id, system_prompt, user_prompt, fallback)
        artifact_path = self.artifact_manager.write("execution-plan", content)
        logs.append(self.log(f"Wrote execution plan to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[artifact_path],
            logs=logs,
            artifact_text=content,
        )
