"""Idea Generation Agent: turns a raw user prompt into a structured idea brief."""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.tools.social_trends import SocialTrendClient
from src.tools.web_search import search_web

logger = logging.getLogger(__name__)


@dataclass
class IdeaGenerationAgent(BaseAgent):
    id: str = "idea-generation"
    name: str = "Idea Generation Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []

        # Gather lightweight trend signals.
        search_context = []
        try:
            web_results = search_web(context.idea, max_results=3)
            search_context.append("## Web search results")
            for r in web_results:
                search_context.append(f"- {r.title}: {r.snippet}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Web search failed for idea generation: %s", exc)
            search_context.append("(web search unavailable)")

        try:
            social_client = SocialTrendClient()
            social_posts = social_client.search_x(context.idea, max_results=3)
            search_context.append("## Social trend signals")
            for p in social_posts:
                search_context.append(f"- {p.author or 'unknown'}: {p.text}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Social trend search failed: %s", exc)
            search_context.append("(social search unavailable)")

        user_prompt = f"""Original prompt: {context.idea}

Trend signals:
{chr(10).join(search_context)}

Write a concise startup idea brief using the sections below."""

        system_prompt = (
            "You are the Idea Generation Agent. Reframe the user's prompt into a "
            "structured startup idea brief with these sections:\n"
            "1. Idea Title\n"
            "2. Problem Statement\n"
            "3. Proposed Solution\n"
            "4. Target Customer\n"
            "5. Value Proposition\n"
            "6. Assumptions to Validate\n"
            "7. Constraints\n\n"
            "Keep the output focused and concise. Do not write code or architecture."
        )

        fallback = f"""# Idea Brief

## Idea Title
{context.idea}

## Problem Statement
The user wants to explore a startup around the idea above.

## Proposed Solution
Build a focused MVP that validates the core assumption quickly.

## Target Customer
Early adopters interested in this problem space.

## Value Proposition
A simpler, more efficient way to address the problem than existing alternatives.

## Assumptions to Validate
- There is measurable demand for this solution.
- A viable business model exists.

## Constraints
- Autonomous agent pipeline with limited iteration budget.
"""

        content = call_llm(self.id, system_prompt, user_prompt, fallback)
        artifact_path = self.artifact_manager.write("idea-generation", content)
        logs.append(self.log(f"Wrote idea brief to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[artifact_path],
            logs=logs,
            artifact_text=content,
        )
