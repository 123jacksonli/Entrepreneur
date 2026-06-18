"""Plan Agent: validates the idea and acts as the idea approval gate.

Gathers competitor signals, asks the Architecture Agent for feasibility/flexibility
input, scores the idea, and renders an approve/iterate/stop decision.
"""

import logging
import re
from dataclasses import dataclass, field

from src.agents._utils import ask_architecture_agent, call_llm, parse_decision
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.tools.web_scraper import scrape_url
from src.tools.web_search import search_web

logger = logging.getLogger(__name__)

VALID_DECISIONS = ("approve", "iterate", "stop")


def _extract_score(text: str) -> int | None:
    match = re.search(r"Score:\s*(\d+)/10", text)
    if match:
        return int(match.group(1))
    return None


@dataclass
class PlanAgent(BaseAgent):
    id: str = "plan"
    name: str = "Plan Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []
        idea_brief = context.artifacts.get("idea-generation", context.idea)
        research_report = context.artifacts.get("research", "")

        # 1. Gather competitor signals.
        competitor_context: list[str] = []
        try:
            queries = [
                f"{context.idea} competitors",
                f"{context.idea} alternatives",
                f"{context.idea} reddit reviews",
            ]
            for query in queries:
                results = search_web(query, max_results=3)
                logs.append(self.log(f"Competitor search '{query}' returned {len(results)} results"))
                competitor_context.append(f"### Query: {query}")
                for r in results:
                    competitor_context.append(f"- [{r.title}]({r.url}): {r.snippet}")
                if results:
                    try:
                        page = scrape_url(results[0].url, max_length=1000)
                        if page.text:
                            competitor_context.append(f"  - Summary: {page.text[:1000]}")
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Scrape failed: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Competitor search failed: %s", exc)
            competitor_context.append("(competitor search unavailable)")

        # 2. Ask Architecture Agent for a quick flexibility/feasibility note.
        architecture_note = ask_architecture_agent(
            execution_plan="",
            plan_report=research_report,
            question="What is the smallest viable technical architecture for this idea, and how flexible is it if the scope changes?",
        )
        logs.append(self.log("Got flexibility note from Architecture Agent"))

        user_prompt = f"""Idea brief:
{idea_brief}

Research report:
{research_report}

Competitor signals:
{chr(10).join(competitor_context)}

Architecture / flexibility note:
{architecture_note}

Write a strategic plan report. Score the idea 0-10. On a line by itself include:
Decision: approve|iterate|stop
Score: N/10"""

        system_prompt = (
            "You are the Plan Agent. Analyze the idea and research, then make an "
            "approve/iterate/stop decision. Output these sections:\n"
            "1. Executive Summary\n"
            "2. Competitor Landscape\n"
            "3. Differentiation Hypothesis\n"
            "4. Opportunity Assessment\n"
            "5. Risk Analysis\n"
            "6. Flexibility Notes (from Architecture Agent)\n"
            "7. Score (0-10) — include the line 'Score: N/10'\n"
            "8. Decision (include the line 'Decision: approve|iterate|stop')\n"
            "9. Strategic Recommendations (if approved)\n"
            "10. Iteration Notes (if iterating)\n\n"
            "Be honest: recommend stop or iterate for weak ideas."
        )

        fallback = f"""# Plan Report

## Executive Summary
The idea is worth validating through a small MVP.

## Competitor Landscape
- Existing general-purpose tools address parts of the problem.
- No direct competitor identified offline.

## Differentiation Hypothesis
A focused, agent-assisted workflow can deliver faster time-to-value.

## Opportunity Assessment
Niche opportunity for early adopters seeking automation.

## Risk Analysis
- Unvalidated demand.
- Potential competition from incumbents.

## Flexibility Notes
Keep the MVP architecture simple so scope can pivot quickly.

## Score
Score: 7/10

## Decision
Decision: approve

## Strategic Recommendations
- Scope the MVP to the smallest usable workflow.
- Validate the core assumption before adding features.
"""

        content = call_llm(self.id, system_prompt, user_prompt, fallback)
        decision = parse_decision(content, VALID_DECISIONS, default="approve")
        score = _extract_score(content)
        logs.append(self.log(f"Plan decision: {decision}, score: {score}"))

        artifact_path = self.artifact_manager.write("plan", content)
        logs.append(self.log(f"Wrote plan report to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[artifact_path],
            logs=logs,
            artifact_text=content,
            metadata={"decision": decision, "score": score},
        )
