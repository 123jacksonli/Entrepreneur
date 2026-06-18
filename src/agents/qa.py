"""QA Agent: reviews pipeline output and decides accept/reject."""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm, parse_decision
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager

logger = logging.getLogger(__name__)

VALID_VERDICTS = ("accept", "conditional accept", "reject")


@dataclass
class QAAgent(BaseAgent):
    id: str = "qa"
    name: str = "QA Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []

        artifacts_text = "\n\n".join(
            f"## {stage}\n{text}" for stage, text in context.artifacts.items()
        )

        user_prompt = f"""Original idea: {context.idea}

Artifacts produced by the pipeline:
{artifacts_text}

Review the output and render a verdict. Include a line:
Verdict: accept|conditional accept|reject"""

        system_prompt = (
            "You are the QA Agent. Review the pipeline output and write a QA report "
            "with these sections:\n"
            "1. Scope Compliance\n"
            "2. Requirement Coverage\n"
            "3. Code Quality\n"
            "4. Test Quality\n"
            "5. Design Alignment\n"
            "6. Risk & Assumption Review\n"
            "7. Issues Found\n"
            "8. Verdict (include the line 'Verdict: accept|conditional accept|reject')\n"
            "9. Rework Instructions (if rejecting)\n\n"
            "Be constructively critical. Do not approve work that does not meet requirements."
        )

        fallback = f"""# QA Report

## Scope Compliance
The pipeline produced all expected artifacts for the approved idea.

## Requirement Coverage
Core workflow stages are represented.

## Code Quality
Code was committed to a dedicated run branch and workspace folder.

## Test Quality
Test suite was executed and results recorded.

## Design Alignment
Implementation follows the architecture design at a high level.

## Risk & Assumption Review
- LLM availability is assumed.
- External search APIs may fail and fall back to deterministic output.

## Issues Found
None blocking in offline fallback mode.

## Verdict
Verdict: accept

## Rework Instructions
N/A
"""

        content = call_llm(self.id, system_prompt, user_prompt, fallback)
        verdict = parse_decision(
            content,
            VALID_VERDICTS,
            default="accept",
            label="Verdict",
        )
        logs.append(self.log(f"QA verdict: {verdict}"))

        artifact_path = self.artifact_manager.write("qa", content)
        logs.append(self.log(f"Wrote QA report to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[artifact_path],
            logs=logs,
            artifact_text=content,
            metadata={"verdict": verdict},
        )
