"""Idea Generation Agent: turns a raw user prompt into a structured idea brief.

Gathers the latest web and social signals, scrapes key pages, and synthesizes
a data-driven idea brief.
"""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm, parse_thinking_output
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.tools.social_trends import SocialTrendClient
from src.tools.web_scraper import scrape_url
from src.tools.web_search import search_web

logger = logging.getLogger(__name__)


@dataclass
class IdeaGenerationAgent(BaseAgent):
    id: str = "idea-generation"
    name: str = "Idea Generation Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []

        # 1. Web search for latest trends and related products.
        search_context: list[str] = []
        try:
            web_results = search_web(context.idea, max_results=5)
            logs.append(self.log(f"Web search returned {len(web_results)} results"))
            search_context.append("## Web search results")
            for r in web_results:
                search_context.append(f"- {r.title} ({r.url}): {r.snippet}")

            # Scrape the top 2 result pages for deeper signals.
            scraped: list[str] = []
            for r in web_results[:2]:
                try:
                    page = scrape_url(r.url, max_length=1500)
                    if page.text:
                        scraped.append(
                            f"### {page.title or r.title}\n{page.text[:1500]}"
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not scrape %s: %s", r.url, exc)
            if scraped:
                search_context.append("## Scraped page summaries")
                search_context.extend(scraped)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Web search/scraping failed for idea generation: %s", exc)
            search_context.append("(web search unavailable)")

        # 2. Social media trend signals.
        try:
            social_client = SocialTrendClient()
            social_posts = social_client.search_all(context.idea, max_results=8)
            logs.append(self.log(f"Social search returned {len(social_posts)} signals"))
            search_context.append("## Social trend signals")
            for p in social_posts:
                search_context.append(
                    f"- {p.platform}: {p.text[:280]} (source: {p.url})"
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Social trend search failed: %s", exc)
            search_context.append("(social search unavailable)")

        user_prompt = f"""Original prompt: {context.idea}

Latest signals:
{chr(10).join(search_context)}

First, write a concise thinking section that explains how you selected and
synthesized the idea. Then write the final structured startup idea brief."""

        system_prompt = (
            "You are the Idea Generation Agent. Reframe the user's prompt into a "
            "structured startup idea brief. Respond in two sections:\n"
            "1. ## Thinking — your reasoning, assumptions, and why this idea is promising.\n"
            "2. ## Output — the final idea brief with these sub-sections:\n"
            "   - Idea Title\n"
            "   - Problem Statement\n"
            "   - Proposed Solution\n"
            "   - Target Customer\n"
            "   - Value Proposition\n"
            "   - Key Signals & Sources\n"
            "   - Assumptions to Validate\n"
            "   - Constraints\n\n"
            "Idea quality constraints:\n"
            "- Propose ideas that can be built as a small, self-contained MVP: a CLI tool, "
            "a Python/Node.js library, a static site, or a tiny local web app.\n"
            "- Avoid ideas that require hosted backends, databases, authentication, multiple "
            "third-party integrations, or paid APIs as part of the core MVP.\n"
            "- The MVP should be testable with standard tools and runnable after a single "
            "install command.\n"
            "- Prefer clear input/output and deterministic behavior so tests are easy to write.\n\n"
            "Use the latest data. Do not write code or architecture."
        )

        fallback = f"""## Thinking

No external data was available, so this fallback uses the original prompt as the
idea seed and fills a generic but complete brief.

## Output

# Idea Brief

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

## Key Signals & Sources
- Web and social search were unavailable offline.

## Assumptions to Validate
- There is measurable demand for this solution.
- A viable business model exists.

## Constraints
- Autonomous agent pipeline with limited iteration budget.
"""

        full_response = call_llm(self.id, system_prompt, user_prompt, fallback)
        thinking, output = parse_thinking_output(full_response)

        thinking_path = self.artifact_manager.write("idea-generation-thinking", thinking)
        logs.append(self.log(f"Wrote idea thinking to {thinking_path}"))

        artifact_path = self.artifact_manager.write("idea-generation", output)
        logs.append(self.log(f"Wrote idea brief to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[thinking_path, artifact_path],
            logs=logs,
            artifact_text=output,
        )
