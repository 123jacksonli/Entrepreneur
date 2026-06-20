"""Execution Agent: turns the approved plan into code and commits it.

The Execution Agent is the only agent allowed to modify implementation files.
It creates a dedicated branch for every pipeline run **and** a dedicated
workspace folder so multiple runs can be developed and tested in isolation.
"""

import logging
import re
from dataclasses import dataclass, field

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.execution_workspace import (
    list_workspace_files,
    prepare_workspace,
    write_workspace_file,
)
from src.tools import git_ops

logger = logging.getLogger(__name__)


@dataclass
class ExecutionAgent(BaseAgent):
    id: str = "execution"
    name: str = "Execution Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the implementation phase for a run.

        Steps:
        1. Create a dedicated branch for the run.
        2. Create a dedicated workspace folder for the run.
        3. Build an implementation summary from prior artifacts.
        4. Generate actual implementation files using the LLM.
        5. Write files into the run workspace.
        6. Write the summary to ``outputs/05-implementation-summary.md``.
        7. Commit and push the milestone to the run branch.
        """
        logs: list = []
        outputs: list[str] = []
        paths_to_commit: list[str] = []

        # 1. Isolate this run's work on its own branch.
        branch_name = git_ops.create_run_branch(context.run_id)
        logs.append(self.log(f"Created execution branch {branch_name}"))

        # 2. Isolate this run's files in their own workspace directory.
        workspace_path = prepare_workspace(context.run_id)
        logs.append(self.log(f"Prepared workspace {workspace_path}"))

        # 3. Gather prior artifacts.
        idea = context.artifacts.get("idea-generation", context.idea) or context.idea
        execution_plan = context.artifacts.get("execution-plan", "")
        architecture = context.artifacts.get("architecture", "")

        # 4. Generate code/config/test files from the plan and architecture.
        generated_files = self._generate_code_files(
            run_id=context.run_id,
            idea=idea,
            execution_plan=execution_plan,
            architecture=architecture,
        )
        for relative_path, content in generated_files.items():
            file_path = write_workspace_file(context.run_id, relative_path, content)
            paths_to_commit.append(str(file_path))
            logs.append(self.log(f"Wrote workspace file {relative_path}"))

        # Also write the workspace README for human orientation.
        workspace_readme = write_workspace_file(
            context.run_id,
            "README.md",
            self._build_workspace_readme(
                run_id=context.run_id,
                idea=idea,
                execution_plan=execution_plan,
            ),
        )
        paths_to_commit.append(str(workspace_path))
        logs.append(self.log(f"Wrote workspace README to {workspace_readme}"))

        # 5. Produce the implementation summary artifact.
        workspace_files = list_workspace_files(context.run_id)
        summary = self._build_summary(
            run_id=context.run_id,
            branch=branch_name,
            workspace=str(workspace_path),
            idea=idea,
            execution_plan=execution_plan,
            architecture=architecture,
            files=workspace_files,
        )
        artifact_path = self.artifact_manager.write("execution", summary)
        outputs.append(artifact_path)
        paths_to_commit.append(artifact_path)
        logs.append(self.log(f"Wrote implementation summary to {artifact_path}"))

        # 6. Commit and push the milestone without human confirmation.
        commit_result = git_ops.commit_milestone(
            run_id=context.run_id,
            message=f"feat: milestone implementation for {context.run_id}",
            paths=paths_to_commit,
        )
        logs.append(
            self.log(
                f"Committed {commit_result.commit_hash[:8]} to {commit_result.branch}; "
                f"remote={commit_result.remote_url}"
            )
        )

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
            "Include at least one source file and one test file when possible."
        )
        user_prompt = f"""Run ID: {run_id}

## Approved Idea

{idea}

## Execution Plan

{execution_plan or "_No execution plan provided._"}

## Architecture

{architecture or "_No architecture design provided._"}

Generate the implementation files now.
"""
        fallback = self._fallback_code_files(run_id, idea)
        response = call_llm("execution", system_prompt, user_prompt, fallback)
        return self._parse_code_files(response)

    def _parse_code_files(self, text: str) -> dict[str, str]:
        """Parse FILE:/fenced-block output from the LLM into a path->content map."""
        files: dict[str, str] = {}
        # Match a FILE: line followed by a fenced code block.
        pattern = re.compile(
            r"^FILE:\s*(.+?)\s*\n```(?:\w+)?\s*\n(.*?)\n```",
            re.MULTILINE | re.DOTALL,
        )
        for match in pattern.finditer(text):
            path = match.group(1).strip().lstrip("/")
            content = match.group(2)
            if path:
                files[path] = content
        return files

    def _fallback_code_files(self, run_id: str, idea: str) -> str:
        """Minimal deterministic fallback if the LLM is unavailable."""
        return f"""FILE: README.md
```markdown
# Run Workspace: {run_id}

{idea}

## Notes

This README was generated as a fallback because the LLM was unavailable.
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
        branch: str,
        workspace: str,
        idea: str,
        execution_plan: str,
        architecture: str,
        files: list[str],
    ) -> str:
        file_list = "\n".join(f"- `{f}`" for f in files) or "_No files generated._"
        return f"""# Implementation Summary

**Run:** {run_id}  
**Branch:** {branch}  
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

1. Check out the run branch: `git checkout {branch}`
2. Inspect the workspace: `cd {workspace}`
3. Install dependencies and run tests.

## Tests Included

- Tests are included in the workspace where applicable; the Test Agent will
  validate them in the next pipeline stage.

## File Manifest

{file_list}

## Known Limitations

- This is an autonomous execution milestone. Review generated files under
  `{workspace}` before merging to `main`.
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
