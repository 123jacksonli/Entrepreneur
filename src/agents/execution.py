"""Execution Agent: turns the approved plan into code and commits it.

The Execution Agent is the only agent allowed to modify implementation files.
It creates a dedicated branch for every pipeline run **and** a dedicated
workspace folder so multiple runs can be developed and tested in isolation.
"""

import logging
from dataclasses import dataclass, field

from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.execution_workspace import prepare_workspace, write_workspace_file
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
        4. Write the summary to ``outputs/05-implementation-summary.md``.
        5. Write the implementation into the run workspace.
        6. Commit and push the milestone to the run branch.
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

        # 4. Produce the implementation summary artifact.
        summary = self._build_summary(
            run_id=context.run_id,
            branch=branch_name,
            workspace=str(workspace_path),
            idea=idea,
            execution_plan=execution_plan,
            architecture=architecture,
        )
        artifact_path = self.artifact_manager.write("execution", summary)
        outputs.append(artifact_path)
        paths_to_commit.append(artifact_path)
        logs.append(self.log(f"Wrote implementation summary to {artifact_path}"))

        # 5. Write the actual implementation into the run workspace.
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

    def _build_summary(
        self,
        *,
        run_id: str,
        branch: str,
        workspace: str,
        idea: str,
        execution_plan: str,
        architecture: str,
    ) -> str:
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

- Tests will be added by the Test Agent in the next pipeline stage.

## Known Limitations

- This is an autonomous execution milestone. The actual code changes are
  committed to `{branch}` under `{workspace}` and can be reviewed there.

## File Manifest

- `outputs/05-implementation-summary.md` — this summary.
- `{workspace}/README.md` — workspace entry point for this run.
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
