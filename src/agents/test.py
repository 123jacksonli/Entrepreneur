"""Test Agent: installs dependencies and runs tests for the generated project."""

import asyncio
import json
import logging
import shutil
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

Write a test report. Be precise about whether tests passed, failed, or were not discovered."""

        system_prompt = (
            "You are the Test Agent. Produce a test report with these sections:\n"
            "1. Test Strategy\n"
            "2. Test Results (include exact pass/fail/error counts if available)\n"
            "3. Coverage Summary\n"
            "4. Bugs Found\n"
            "5. Flaky or Skipped Tests\n"
            "6. Recommendation\n\n"
            "Do not fix bugs; only report findings. If zero tests were discovered or "
            "the test runner failed to start, state that clearly."
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

    def _detect_project_type(self, workspace: Path) -> str:
        """Detect whether the workspace is a Python or Node.js project."""
        if (workspace / "package.json").exists():
            return "node"
        if any(
            (workspace / name).exists()
            for name in ("requirements.txt", "pyproject.toml", "setup.py", "setup.cfg")
        ):
            return "python"
        return "unknown"

    def _install_project_dependencies(self, workspace: Path, project_type: str) -> str:
        """Install dependencies declared by the generated project."""
        workspace = workspace.resolve()

        if project_type == "node":
            if shutil.which("npm") is None:
                return "npm not available; cannot install Node.js dependencies."
            cmd = ["npm", "install"]
        elif project_type == "python":
            req_file = workspace / "requirements.txt"
            if req_file.exists():
                cmd = ["python", "-m", "pip", "install", "-r", str(req_file)]
            else:
                cmd = ["python", "-m", "pip", "install", "-e", "."]
        else:
            return "No dependency manifest found; skipping install."

        try:
            result = subprocess.run(
                cmd,
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout + "\n" + result.stderr
            return output.strip()
        except subprocess.TimeoutExpired:
            return "Dependency installation timed out."
        except Exception as exc:  # noqa: BLE001
            return f"Error installing dependencies: {exc}"

    def _run_node_tests(self, workspace: Path) -> subprocess.CompletedProcess:
        """Run tests in a Node.js workspace using the package.json test script."""
        package_json = workspace / "package.json"
        scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {})
        test_script = scripts.get("test", "")
        node_modules = workspace / "node_modules"

        def runner_exists(name: str) -> bool:
            return (node_modules / ".bin" / name).exists() or shutil.which(name) is not None

        test_script_lower = test_script.lower()
        if "vitest" in test_script_lower or runner_exists("vitest"):
            cmd = ["npx", "vitest", "run", "--reporter=verbose"]
        elif "jest" in test_script_lower or runner_exists("jest"):
            cmd = ["npx", "jest", "--runInBand"]
        elif test_script:
            # Generic test script; run it once. Avoid watch-mode scripts.
            cmd = ["npm", "test", "--", "--run"]
        else:
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="No 'test' script in package.json and no test runner found.",
            )

        return subprocess.run(
            cmd,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=300,
        )

    def _run_python_tests(self, workspace: Path) -> subprocess.CompletedProcess:
        """Run tests in a Python workspace."""
        test_dirs = [workspace / "tests", workspace / "test"]
        test_dir = next((d for d in test_dirs if d.exists() and d.is_dir()), None)

        if test_dir is None:
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="No tests/ or test/ directory found in the generated project.",
            )

        return subprocess.run(
            ["python", "-m", "pytest", str(test_dir), "-q"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=300,
        )

    def _run_project_tests(self, run_id: str) -> str:
        """Run tests inside the generated project workspace for a run."""
        workspace = Path(Config.WORKSPACE_DIR) / run_id
        workspace = workspace.resolve()
        if not workspace.exists():
            return f"Workspace {workspace} does not exist; no tests to run."

        project_type = self._detect_project_type(workspace)
        install_log = self._install_project_dependencies(workspace, project_type)

        if project_type == "unknown":
            return f"Could not detect project type (no package.json, pyproject.toml, requirements.txt, or setup.py).\n\nDependency install log:\n{install_log}"

        if project_type == "node":
            result = self._run_node_tests(workspace)
        else:
            result = self._run_python_tests(workspace)

        output = result.stdout + "\n" + result.stderr
        return (
            f"Project type: {project_type}\n"
            f"Dependency install log:\n{install_log}\n\n"
            f"Test exit code: {result.returncode}\n"
            f"Test output:\n{output.strip()}"
        )
