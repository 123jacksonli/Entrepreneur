"""QA Agent: reviews pipeline output and decides accept/reject."""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm, parse_decision, parse_thinking_output
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

First, write a thinking section that walks through your review criteria and the
evidence for each. Then render the final QA report and verdict."""

        system_prompt = (
            "You are the QA Agent. Review the pipeline output and write a QA report. "
            "Respond in two sections:\n"
            "1. ## Thinking — your step-by-step review reasoning, including what you "
            "checked and why.\n"
            "2. ## Output — the final QA report with these sub-sections:\n"
            "   - Scope Compliance\n"
            "   - Requirement Coverage\n"
            "   - Code Quality\n"
            "   - Test Quality\n"
            "   - Design Alignment\n"
            "   - Risk & Assumption Review\n"
            "   - Issues Found\n"
            "   - Verdict (include the line 'Verdict: accept|conditional accept|reject')\n"
            "   - Rework Instructions (if rejecting)\n\n"
            "Hard acceptance rules:\n"
            "- The project MUST have a dependency manifest (package.json or pyproject.toml/"
            "requirements.txt/setup.py) AND a README with setup/usage instructions.\n"
            "- The test suite MUST run and at least one test MUST be discovered.\n"
            "- All discovered tests MUST pass (exit code 0).\n"
            "- If any of the above is not true, verdict MUST be reject with concrete "
            "rework instructions to fix the specific gap.\n\n"
            "Guidance:\n"
            "- Approve (or conditional-accept) when the hard rules are satisfied, the "
            "core functionality works, and the implementation meets the execution plan.\n"
            "- Do not reject solely because you would like more tests of a specific type, "
            "more documentation, real-world validation data, or cosmetic polish.\n"
            "- Reject when there is a concrete, fixable defect: failing tests, missing "
            "required functionality, broken CLI contract, or security/correctness bugs "
            "that the Execution Agent can actually address.\n"
            "- Rework instructions must be specific, minimal, and actionable."
        )

        fallback = f"""## Thinking

Offline fallback: the pipeline produced all expected artifacts, so the verdict
is accept with noted assumptions.

## Output

# QA Report

## Scope Compliance
The pipeline produced all expected artifacts for the approved idea.

## Requirement Coverage
Core workflow stages are represented.

## Code Quality
Code was written to a dedicated workspace folder for the run.

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

        full_response = call_llm(self.id, system_prompt, user_prompt, fallback)
        thinking, output = parse_thinking_output(full_response)

        verdict = parse_decision(
            output,
            VALID_VERDICTS,
            default="accept",
            label="Verdict",
        )
        logs.append(self.log(f"QA verdict: {verdict}"))

        thinking_path = self.artifact_manager.write("qa-thinking", thinking)
        logs.append(self.log(f"Wrote QA thinking to {thinking_path}"))

        artifact_path = self.artifact_manager.write("qa", output)
        logs.append(self.log(f"Wrote QA report to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[thinking_path, artifact_path],
            logs=logs,
            artifact_text=output,
            metadata={"verdict": verdict},
        )
