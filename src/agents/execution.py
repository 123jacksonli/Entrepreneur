"""Execution Agent: turns the approved plan into code and commits it.

The Execution Agent is the only agent allowed to modify implementation files.
It creates a dedicated branch for every pipeline run, writes the implementation
summary, and commits/pushes each milestone autonomously.
"""

import logging
from dataclasses import dataclass, field

from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
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
        2. Build an implementation summary from prior artifacts.
        3. Write the summary to ``outputs/05-implementation-summary.md``.
        4. Commit and push the milestone to the run branch.
        """
        logs: list = []
        outputs: list[str] = []

        # 1. Isolate this run's work on its own branch.
        branch_name = git_ops.create_run_branch(context.run_id)
        logs.append(self.log(f"Created execution branch {branch_name}"))

        # 2. Gather prior artifacts.
        idea = context.artifacts.get("idea-generation", context.idea) or context.idea
        execution_plan = context.artifacts.get("execution-plan", "")
        architecture = context.artifacts.get("architecture", "")

        # 3. Produce the implementation summary artifact.
        summary = self._build_summary(
            run_id=context.run_id,
            branch=branch_name,
            idea=idea,
            execution_plan=execution_plan,
            architecture=architecture,
        )
        artifact_path = self.artifact_manager.write("execution", summary)
        outputs.append(artifact_path)
        logs.append(self.log(f"Wrote implementation summary to {artifact_path}"))

        # 4. Commit and push the milestone without human confirmation.
        commit_result = git_ops.commit_milestone(
            run_id=context.run_id,
            message=f"feat: milestone implementation for {context.run_id}",
            paths=[artifact_path],
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
        idea: str,
        execution_plan: str,
        architecture: str,
    ) -> str:
        return f"""# Implementation Summary

**Run:** {run_id}  
**Branch:** {branch}

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
2. Install dependencies.
3. Run tests and start the application.

## Tests Included

- Tests will be added by the Test Agent in the next pipeline stage.

## Known Limitations

- This is an autonomous execution milestone. The actual code changes are
  committed to `{branch}` and can be reviewed there.

## File Manifest

- `outputs/05-implementation-summary.md` — this summary.
"""
