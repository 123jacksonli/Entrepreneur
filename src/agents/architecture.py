"""Architecture Agent: designs the technical blueprint for the Execution Agent."""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm, parse_thinking_output
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

First, write a thinking section that explains your architectural trade-offs and
why you selected the proposed stack. Then design the buildable architecture for
the MVP."""

        system_prompt = (
            "You are the Architecture Agent. Design the technical blueprint. "
            "Respond in two sections:\n"
            "1. ## Thinking — your architectural reasoning, trade-offs, and why the "
            "chosen stack fits the MVP constraints.\n"
            "2. ## Output — the final architecture design with these sub-sections:\n"
            "   - Overview\n"
            "   - Tech Stack\n"
            "   - System Components\n"
            "   - Data Model\n"
            "   - API Contracts\n"
            "   - Integration Points\n"
            "   - Deployment & Infrastructure\n"
            "   - Non-Functional Requirements\n"
            "   - Open Questions for Human Review\n\n"
            "Design constraints:\n"
            "- Prefer the simplest stack that can deliver the MVP. A single Python or "
            "Node.js CLI/library, a static site, or a tiny local web app is better than "
            "a multi-service architecture.\n"
            "- Avoid external dependencies such as databases, cloud hosting, auth providers, "
            "or paid APIs unless absolutely required by the core value proposition.\n"
            "- Use file-based or in-memory state when possible.\n"
            "- The MVP must be testable with standard tools (pytest, vitest, jest) and "
            "runnable on a fresh clone after a single install command.\n\n"
            "Do not write production code or implementation details."
        )

        fallback = f"""## Thinking

Offline fallback: a simple, proven stack is chosen to minimize risk and speed up
MVP delivery.

## Output

# Architecture Design

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

        full_response = call_llm(self.id, system_prompt, user_prompt, fallback)
        thinking, output = parse_thinking_output(full_response)

        thinking_path = self.artifact_manager.write("architecture-thinking", thinking)
        logs.append(self.log(f"Wrote architecture thinking to {thinking_path}"))

        artifact_path = self.artifact_manager.write("architecture", output)
        logs.append(self.log(f"Wrote architecture design to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[thinking_path, artifact_path],
            logs=logs,
            artifact_text=output,
        )
