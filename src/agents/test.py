"""Test Agent: runs tests and reports results."""

import asyncio
import logging
import subprocess
from dataclasses import dataclass, field

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager

logger = logging.getLogger(__name__)


@dataclass
class TestAgent(BaseAgent):
    __test__ = False  # Tell pytest this is not a test class.
    id: str = "test"
    name: str = "Test Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []

        # Run the backend test suite in a thread-safe way.
        test_output = await asyncio.to_thread(self._run_pytest)
        logs.append(self.log("Ran backend test suite"))

        implementation_summary = context.artifacts.get("execution", "")
        architecture = context.artifacts.get("architecture", "")

        user_prompt = f"""Implementation summary:
{implementation_summary}

Architecture notes:
{architecture}

Test output:
```
{test_output}
```

Write a test report."""

        system_prompt = (
            "You are the Test Agent. Produce a test report with these sections:\n"
            "1. Test Strategy\n"
            "2. Test Results\n"
            "3. Coverage Summary\n"
            "4. Bugs Found\n"
            "5. Flaky or Skipped Tests\n"
            "6. Recommendation\n\n"
            "Do not fix bugs; only report findings."
        )

        fallback = f"""# Test Report

## Test Strategy
Ran the existing automated test suite to verify core backend and agent tooling behavior.

## Test Results
```
{test_output}
```

## Coverage Summary
Coverage was not measured in this automated pass.

## Bugs Found
None reported by the test runner.

## Flaky or Skipped Tests
- Some tests depend on external web search and may fail due to network issues.

## Recommendation
Proceed to QA review if the test runner reports no failures.
"""

        content = call_llm(self.id, system_prompt, user_prompt, fallback)
        artifact_path = self.artifact_manager.write("test", content)
        logs.append(self.log(f"Wrote test report to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[artifact_path],
            logs=logs,
            artifact_text=content,
        )

    def _run_pytest(self) -> str:
        """Run pytest and return stdout/stderr combined."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout + "\n" + result.stderr
            return output.strip()
        except subprocess.TimeoutExpired:
            return "Test suite timed out."
        except FileNotFoundError:
            return "pytest not available."
        except Exception as exc:  # noqa: BLE001
            return f"Error running tests: {exc}"
