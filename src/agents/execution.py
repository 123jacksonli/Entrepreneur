"""Execution Agent: turns the approved plan into code.

The Execution Agent is the only agent allowed to modify implementation files.
It writes all generated code, config, tests, and docs into a dedicated
workspace folder under ``workspace/{run_id}/`` so multiple runs can be
developed and tested in isolation.
"""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.execution_workspace import (
    list_workspace_files,
    prepare_workspace,
    write_workspace_file,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionAgent(BaseAgent):
    id: str = "execution"
    name: str = "Execution Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the implementation phase for a run.

        Steps:
        1. Create a dedicated workspace folder for the run.
        2. Build an implementation summary from prior artifacts.
        3. Generate actual implementation files using the LLM.
        4. Write files into the run workspace.
        5. Write the summary to ``outputs/05-implementation-summary.md``.
        """
        logs: list = []
        outputs: list[str] = []

        # 1. Isolate this run's files in their own workspace directory.
        workspace_path = prepare_workspace(context.run_id)
        logs.append(self.log(f"Prepared workspace {workspace_path}"))

        # 2. Gather prior artifacts.
        idea = context.artifacts.get("idea-generation", context.idea) or context.idea
        execution_plan = context.artifacts.get("execution-plan", "")
        architecture = context.artifacts.get("architecture", "")
        test_report = context.artifacts.get("test", "")
        qa_report = context.artifacts.get("qa", "")

        # 3. Generate code/config/test files from the plan and architecture.
        generated_files = self._generate_code_files(
            run_id=context.run_id,
            idea=idea,
            execution_plan=execution_plan,
            architecture=architecture,
            test_report=test_report,
            qa_report=qa_report,
        )
        for relative_path, content in generated_files.items():
            write_workspace_file(context.run_id, relative_path, content)
            logs.append(self.log(f"Wrote workspace file {relative_path}"))

        # Also write the workspace README for human orientation.
        write_workspace_file(
            context.run_id,
            "README.md",
            self._build_workspace_readme(
                run_id=context.run_id,
                idea=idea,
                execution_plan=execution_plan,
            ),
        )

        # 4. Produce the implementation summary artifact.
        workspace_files = list_workspace_files(context.run_id)
        summary = self._build_summary(
            run_id=context.run_id,
            workspace=str(workspace_path),
            idea=idea,
            execution_plan=execution_plan,
            architecture=architecture,
            files=workspace_files,
        )
        artifact_path = self.artifact_manager.write("execution", summary)
        outputs.append(artifact_path)
        logs.append(self.log(f"Wrote implementation summary to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=outputs,
            logs=logs,
            artifact_text=summary,
        )

    def _generate_code_files(
        self,
        *,
        run_id: str,
        idea: str,
        execution_plan: str,
        architecture: str,
        test_report: str,
        qa_report: str,
    ) -> dict[str, str]:
        """Ask the LLM to produce implementation files and return a path->content map."""
        system_prompt = (
            "You are the Execution Agent for an autonomous startup builder. "
            "Your job is to turn an approved startup idea, execution plan, and architecture "
            "into a small but concrete set of implementation files (code, config, tests, docs). "
            "Produce only files needed for a minimal runnable MVP. Do not include long explanations. "
            "Return every file in the exact format below:\n\n"
            "FILE: relative/path/to/file.ext\n"
            "```ext\n"
            "# file content\n"
            "```\n\n"
            "Use the same format for every file. Paths must be relative to the project root. "
            "Include at least one source file and one test file when possible.\n\n"
            "Critical requirements:\n"
            "- Always include a dependency manifest (package.json for Node.js, pyproject.toml "
            "or requirements.txt for Python).\n"
            "- Always include a README.md with install and run instructions.\n"
            "- For Node.js, include a 'test' script in package.json that runs the tests.\n"
            "- For Python, place tests under tests/ and use pytest.\n"
            "- Keep the MVP self-contained: avoid external services (databases, APIs, cloud "
            "infra) unless the architecture explicitly requires them. Prefer in-memory or "
            "file-based implementations for the MVP."
        )

        rework_section = ""
        if qa_report:
            rework_section = f"""
## Previous QA Feedback

{qa_report}

You are running a rework iteration. Address the issues above explicitly. Be
conservative: preserve the existing implementation and tests as much as possible
and only change files necessary to fix the reported defects. Do not add new
files or expand scope unless the rework instructions require it. In your
implementation summary, list what changed compared to the previous iteration.
"""
        if test_report:
            rework_section += f"""
## Previous Test Report

{test_report}

Fix any reported bugs or gaps where feasible.
"""

        user_prompt = f"""Run ID: {run_id}

## Approved Idea

{idea}

## Execution Plan

{execution_plan or "_No execution plan provided._"}

## Architecture

{architecture or "_No architecture design provided._"}
{rework_section}
Generate the implementation files now.
"""
        fallback = self._fallback_code_files(run_id, idea, bool(qa_report))
        response = call_llm("execution", system_prompt, user_prompt, fallback)
        return self._parse_code_files(response)

    def _parse_code_files(self, text: str) -> dict[str, str]:
        """Parse FILE:/fenced-block output from the LLM into a path->content map.

        The expected format for each file is:

            FILE: relative/path/to/file.ext
            ```ext
            # file content
            ```

        This parser is line-based so it handles empty files, files whose content
        contains triple backticks, and multiple files in a single response.
        """
        import re

        files: dict[str, str] = {}
        current_path: str | None = None
        current_lines: list[str] = []
        in_fence = False

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("FILE:"):
                if current_path is not None:
                    files[current_path] = "\n".join(current_lines).rstrip("\n")
                current_path = stripped[len("FILE:"):].strip().lstrip("/")
                current_lines = []
                in_fence = False
                continue

            if current_path is None:
                continue

            fence_match = re.match(r"^```(?:\w+)?\s*$", stripped)
            if fence_match and not in_fence:
                in_fence = True
                continue

            if stripped == "```" and in_fence:
                files[current_path] = "\n".join(current_lines).rstrip("\n")
                current_path = None
                current_lines = []
                in_fence = False
                continue

            if in_fence:
                current_lines.append(line)

        # If the response ends while still collecting a file, flush it.
        if current_path is not None:
            files[current_path] = "\n".join(current_lines).rstrip("\n")

        return files

    def _fallback_code_files(self, run_id: str, idea: str, is_rework: bool) -> str:
        """Minimal deterministic fallback if the LLM is unavailable."""
        rework_note = "This is a rework iteration." if is_rework else ""
        return f"""FILE: README.md
```markdown
# Run Workspace: {run_id}

{idea}

## Notes

This README was generated as a fallback because the LLM was unavailable.
{rework_note}
```

FILE: src/main.py
```python
# Fallback main entry point for {run_id}

def main() -> None:
    print("Hello from {run_id}!")

if __name__ == "__main__":
    main()
```

FILE: tests/test_main.py
```python
from src.main import main


def test_main_runs() -> None:
    assert main() is None
```
"""

    def _build_summary(
        self,
        *,
        run_id: str,
        workspace: str,
        idea: str,
        execution_plan: str,
        architecture: str,
        files: list[str],
    ) -> str:
        file_list = "\n".join(f"- `{f}`" for f in files) or "_No files generated._"
        return f"""# Implementation Summary

**Run:** {run_id}  
**Workspace:** `{workspace}`

## What Was Built

Implementation for the approved idea:

> {idea}

## Milestones Completed

Based on the execution plan and architecture design, the following milestones
were targeted:

{execution_plan or "_No execution plan provided._"}

## Architecture Notes

{architecture or "_No architecture design provided._"}

## How to Run

1. Inspect the workspace: `cd {workspace}`
2. Install dependencies and run tests.

## Tests Included

- Tests are included in the workspace where applicable; the Test Agent will
  validate them in the next pipeline stage.

## File Manifest

{file_list}

## Known Limitations

- This is an autonomous execution milestone. Review generated files under
  `{workspace}` before using them in production.
"""

    def _build_workspace_readme(
        self,
        *,
        run_id: str,
        idea: str,
        execution_plan: str,
    ) -> str:
        return f"""# Run Workspace: {run_id}

**Idea:** {idea}

## Execution Plan

{execution_plan or "_No execution plan provided._"}

## Notes

This directory is the isolated workspace for run `{run_id}`. The Execution
Agent writes code, config, and tests here so that multiple runs can be
implemented and tested without overwriting each other.
"""
