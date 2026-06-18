"""Architecture Agent: designs the technical blueprint for the Execution Agent."""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureAgent(BaseAgent):
    id: str = "architecture"
    name: str = "Architecture Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []
        plan_report = context.artifacts.get("plan", "")
        execution_plan = context.artifacts.get("execution-plan", "")

        user_prompt = f"""Plan report:
{plan_report}

Execution plan:
{execution_plan}

Design a buildable architecture for the MVP."""

        system_prompt = (
            "You are the Architecture Agent. Design the technical blueprint with "
            "these sections:\n"
            "1. Overview\n"
            "2. Tech Stack\n"
            "3. System Components\n"
            "4. Data Model\n"
            "5. API Contracts\n"
            "6. Integration Points\n"
            "7. Deployment & Infrastructure\n"
            "8. Non-Functional Requirements\n"
            "9. Open Questions for Human Review\n\n"
            "Do not write production code or implementation details."
        )

        fallback = f"""# Architecture Design

## Overview
A lightweight multi-agent web application with a FastAPI backend and a Next.js frontend.

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, SQLite
- **Frontend:** Next.js 14 + TypeScript + Tailwind
- **LLM:** Zhipu AI via OpenRouter using the OpenAI-compatible SDK
- **Workflow graph:** @xyflow/react

## System Components
- **Orchestrator:** drives the pipeline state machine.
- **State Store:** persists runs in SQLite.
- **Artifact Manager:** reads/writes markdown artifacts.
- **Agents:** specialized stage implementations.
- **Frontend Dashboard:** visualizes pipeline and history.

## Data Model
- `Run`: id, idea, status, current_agent_id, timestamps.
- `AgentRun`: id, run_id, agent_id, status, outputs, logs, timestamps.

## API Contracts
- `POST /runs` — start a run.
- `GET /runs/{id}` — get run status.
- `GET /runs/{id}/events` — SSE event stream.
- `GET /runs` — list runs.

## Integration Points
- OpenRouter LLM API.
- DuckDuckGo/SerpAPI for web search.
- GitHub MCP or git CLI for version control.

## Deployment & Infrastructure
- Local development with Uvicorn and `npm run dev`.
- Production: containerized backend + static/Vercel frontend.

## Non-Functional Requirements
- State persisted after every stage.
- Pipeline loops bounded by `MAX_IDEA_ITERATIONS` and `MAX_QA_ITERATIONS`.

## Open Questions for Human Review
- Hosting provider and CI/CD pipeline details.
"""

        content = call_llm(self.id, system_prompt, user_prompt, fallback)
        artifact_path = self.artifact_manager.write("architecture", content)
        logs.append(self.log(f"Wrote architecture design to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[artifact_path],
            logs=logs,
            artifact_text=content,
        )
