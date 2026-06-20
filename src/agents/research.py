"""Research Agent: gathers market data, trends, competitors, and sources.

Uses multiple web searches, page scraping, and social trend signals. If the
idea brief is ambiguous, it asks the Idea Generation Agent for clarification.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.agents._utils import ask_idea_agent, call_llm, parse_thinking_output
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.tools.social_trends import SocialTrendClient
from src.tools.web_scraper import scrape_url
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

        # If the brief is vague, ask the Idea Generation Agent for clarification.
        clarification = ""
        if len(idea_brief) < 100 or "unclear" in idea_brief.lower():
            clarification = ask_idea_agent(
                idea_brief,
                "What is the exact target customer and the top pain point to research?",
            )
            logs.append(self.log("Asked Idea Generation Agent for clarification"))

        queries = [
            f"{context.idea} market size trends 2024",
            f"{context.idea} target customer segments",
            f"{context.idea} competitors alternatives",
            f"{context.idea} pricing benchmark",
            f"{context.idea} latest news",
        ]
        search_results: list[str] = []
        for query in queries:
            try:
                results = search_web(query, max_results=3)
                logs.append(self.log(f"Search '{query}' returned {len(results)} results"))
                search_results.append(f"### Query: {query}")
                for r in results:
                    search_results.append(f"- [{r.title}]({r.url}): {r.snippet}")

                # Scrape first result for deeper content.
                if results:
                    try:
                        page = scrape_url(results[0].url, max_length=1200)
                        if page.text:
                            search_results.append(
                                f"  - Scraped summary: {page.text[:1200]}"
                            )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Scrape failed for %s: %s", results[0].url, exc)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Research search failed for '%s': %s", query, exc)
                search_results.append(f"(search unavailable for: {query})")

        # Social media signals (via web search + scraping).
        try:
            social_client = SocialTrendClient()
            social_posts = social_client.search_all(context.idea, max_results=8)
            logs.append(self.log(f"Social search returned {len(social_posts)} signals"))
            search_results.append("### Social trend signals")
            for p in social_posts:
                search_results.append(
                    f"- {p.platform}: {p.text[:280]} (source: {p.url})"
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Social trend search failed: %s", exc)

        user_prompt = f"""Idea brief:
{idea_brief}

Clarification from Idea Agent:
{clarification or "N/A"}

Research findings:
{chr(10).join(search_results)}

First, write a thinking section that explains how you weighed the evidence and
which claims you are most/least confident about. Then write the final research
report."""

        system_prompt = (
            "You are the Research Agent. Produce a fact-based research report. "
            "Respond in two sections:\n"
            "1. ## Thinking — your reasoning, confidence levels, and how you weighed "
            "conflicting or sparse data.\n"
            "2. ## Output — the final report with these sub-sections:\n"
            "   - Executive Summary\n"
            "   - Problem Statement\n"
            "   - Target Market\n"
            "   - Trends\n"
            "   - Competitor Landscape\n"
            "   - Key Data & Benchmarks\n"
            "   - Risks & Unknowns\n"
            "   - Sources (cite URLs and access dates)\n\n"
            "Do not write code, plans, or final recommendations."
        )

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fallback = f"""## Thinking

No external sources were reachable, so this report is a scaffold with clearly
flagged low-confidence claims.

## Output

# Research Report

## Executive Summary
Initial research for the idea above. Public sources were unavailable offline, so this report is a scaffold.

## Problem Statement
The problem is described in the idea brief.

## Target Market
Early adopters and problem-aware customers in the relevant segment.

## Competitor Landscape
- Existing general-purpose tools address parts of the problem.
- No direct competitor identified offline.

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

        full_response = call_llm(self.id, system_prompt, user_prompt, fallback)
        thinking, output = parse_thinking_output(full_response)

        thinking_path = self.artifact_manager.write("research-thinking", thinking)
        logs.append(self.log(f"Wrote research thinking to {thinking_path}"))

        artifact_path = self.artifact_manager.write("research", output)
        logs.append(self.log(f"Wrote research report to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[thinking_path, artifact_path],
            logs=logs,
            artifact_text=output,
        )
