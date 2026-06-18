"""Research Agent: gathers market data and trends for the idea."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.tools.web_search import search_web

logger = logging.getLogger(__name__)


@dataclass
class ResearchAgent(BaseAgent):
    id: str = "research"
    name: str = "Research Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []
        idea_brief = context.artifacts.get("idea-generation", context.idea)

        queries = [
            f"{context.idea} market size trends",
            f"{context.idea} target customer",
            f"{context.idea} news 2024",
        ]
        search_results: list[str] = []
        for query in queries:
            try:
                results = search_web(query, max_results=3)
                search_results.append(f"### Query: {query}")
                for r in results:
                    search_results.append(f"- [{r.title}]({r.url}): {r.snippet}")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Research search failed for '%s': %s", query, exc)
                search_results.append(f"(search unavailable for: {query})")

        user_prompt = f"""Idea brief:
{idea_brief}

Search findings:
{chr(10).join(search_results)}

Write a research report using the requested sections."""

        system_prompt = (
            "You are the Research Agent. Produce a fact-based research report with "
            "these sections:\n"
            "1. Executive Summary\n"
            "2. Problem Statement\n"
            "3. Target Market\n"
            "4. Trends\n"
            "5. Key Data & Benchmarks\n"
            "6. Risks & Unknowns\n"
            "7. Sources\n\n"
            "Cite URLs where available. Do not write code, competitor analysis, or plans."
        )

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fallback = f"""# Research Report

## Executive Summary
Initial research for the idea above. Public sources were unavailable offline, so this report is a scaffold.

## Problem Statement
The problem is described in the idea brief.

## Target Market
Early adopters and problem-aware customers in the relevant segment.

## Trends
- Growing interest in AI/automation-enabled solutions.
- Increasing demand for lean, focused tools.

## Key Data & Benchmarks
- No verified data points were retrieved offline.

## Risks & Unknowns
- Market size and willingness to pay are unverified.
- Competitive density is unknown.

## Sources
- Web search ({today}) — no external sources retrieved.
"""

        content = call_llm(self.id, system_prompt, user_prompt, fallback)
        artifact_path = self.artifact_manager.write("research", content)
        logs.append(self.log(f"Wrote research report to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[artifact_path],
            logs=logs,
            artifact_text=content,
        )
