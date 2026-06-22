"""Test Agent: runs tests and reports results."""

import asyncio
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.config import Config

logger = logging.getLogger(__name__)


@dataclass
class TestAgent(BaseAgent):
    __test__ = False  # Tell pytest this is not a test class.
    id: str = "test"
    name: str = "Test Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []

        # Run tests against the generated project in the run workspace.
        test_output = await asyncio.to_thread(self._run_project_tests, context.run_id)
        logs.append(self.log("Ran generated project test suite"))

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
Ran the generated project's automated test suite (if present) to verify core behavior.

## Test Results
```
{test_output}
```

## Coverage Summary
Coverage was not measured in this automated pass.

## Bugs Found
None reported by the test runner.

## Flaky or Skipped Tests
- Some tests may depend on external services and can fail due to network issues.

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

    def _install_project_dependencies(self, workspace: Path) -> str:
        """Install dependencies declared by the generated project."""
        workspace = workspace.resolve()
        req_file = workspace / "requirements.txt"
        pyproject = workspace / "pyproject.toml"
        setup_py = workspace / "setup.py"

        if req_file.exists():
            cmd = ["python", "-m", "pip", "install", "-r", str(req_file)]
        elif pyproject.exists() or setup_py.exists():
            cmd = ["python", "-m", "pip", "install", "-e", "."]
        else:
            return "No dependency manifest found; skipping install."

        try:
            result = subprocess.run(
                cmd,
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout + "\n" + result.stderr
            return output.strip()
        except subprocess.TimeoutExpired:
            return "Dependency installation timed out."
        except Exception as exc:  # noqa: BLE001
            return f"Error installing dependencies: {exc}"

    def _run_project_tests(self, run_id: str) -> str:
        """Run tests inside the generated project workspace for a run."""
        workspace = Path(Config.WORKSPACE_DIR) / run_id
        workspace = workspace.resolve()
        if not workspace.exists():
            return f"Workspace {workspace} does not exist; no tests to run."

        install_log = self._install_project_dependencies(workspace)

        test_dirs = [workspace / "tests", workspace / "test"]
        test_dir = next((d for d in test_dirs if d.exists() and d.is_dir()), None)

        if test_dir is None:
            return f"No tests/ or test/ directory found in the generated project.\n\nDependency install log:\n{install_log}"

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_dir), "-q"],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout + "\n" + result.stderr
            return f"Dependency install log:\n{install_log}\n\nTest output:\n{output.strip()}"
        except subprocess.TimeoutExpired:
            return f"Dependency install log:\n{install_log}\n\nTest suite timed out."
        except FileNotFoundError:
            return f"Dependency install log:\n{install_log}\n\npytest not available."
        except Exception as exc:  # noqa: BLE001
            return f"Dependency install log:\n{install_log}\n\nError running tests: {exc}"
