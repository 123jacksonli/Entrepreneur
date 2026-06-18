"""Plan Agent: validates the idea and acts as the idea approval gate."""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm, parse_decision
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.tools.web_search import search_web

logger = logging.getLogger(__name__)

VALID_DECISIONS = ("approve", "iterate", "stop")


@dataclass
class PlanAgent(BaseAgent):
    id: str = "plan"
    name: str = "Plan Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []
        idea_brief = context.artifacts.get("idea-generation", context.idea)
        research_report = context.artifacts.get("research", "")

        try:
            competitor_results = search_web(
                f"{context.idea} competitors alternatives", max_results=3
            )
            competitor_context = "\n".join(
                f"- [{r.title}]({r.url}): {r.snippet}" for r in competitor_results
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Competitor search failed: %s", exc)
            competitor_context = "(competitor search unavailable)"

        user_prompt = f"""Idea brief:
{idea_brief}

Research report:
{research_report}

Competitor signals:
{competitor_context}

Write a strategic plan report. On a line by itself at the start or end, include:
Decision: approve|iterate|stop"""

        system_prompt = (
            "You are the Plan Agent. Analyze the idea and research, then make an "
            "approve/iterate/stop decision. Output these sections:\n"
            "1. Executive Summary\n"
            "2. Competitor Landscape\n"
            "3. Differentiation Hypothesis\n"
            "4. Opportunity Assessment\n"
            "5. Risk Analysis\n"
            "6. Decision (include the line 'Decision: approve|iterate|stop')\n"
            "7. Strategic Recommendations (if approved)\n"
            "8. Iteration Notes (if iterating)\n\n"
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

## Decision
Decision: approve

## Strategic Recommendations
- Scope the MVP to the smallest usable workflow.
- Validate the core assumption before adding features.
"""

        content = call_llm(self.id, system_prompt, user_prompt, fallback)
        decision = parse_decision(content, VALID_DECISIONS, default="approve")
        logs.append(self.log(f"Plan decision: {decision}"))

        artifact_path = self.artifact_manager.write("plan", content)
        logs.append(self.log(f"Wrote plan report to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[artifact_path],
            logs=logs,
            artifact_text=content,
            metadata={"decision": decision},
        )
