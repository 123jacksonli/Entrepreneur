"""Execution Agent: turns the approved plan into production-grade code.

The Execution Agent is the only agent allowed to modify implementation files.
It writes all generated code, config, tests, and docs into a dedicated
workspace folder under ``workspace/{run_id}/`` so multiple runs can be
developed and tested in isolation.

This version is self-healing: after generating files it installs dependencies,
runs tests, type-checks, and lints; if anything fails it asks the LLM for a
fix and regenerates, up to MAX_EXECUTION_FIX_ITERATIONS times.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.config import Config
from src.execution_build import BuildResult, BuildRunner
from src.execution_hygiene import build_hygiene_files
from src.execution_parser import ParserResult, parse_code_files
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
    max_fix_iterations: int = field(
        default_factory=lambda: Config.MAX_EXECUTION_FIX_ITERATIONS
    )

    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the implementation phase for a run.

        Steps:
        1. Create a dedicated workspace folder for the run.
        2. Build an implementation prompt from prior artifacts.
        3. Generate implementation files using the LLM.
        4. Parse, sanitize, and write files into the run workspace.
        5. Write production-hygiene files (.gitignore, CI, etc.).
        6. Run the inner build/test/fix loop until the project passes or the
           iteration budget is exhausted.
        7. Write the implementation summary artifact.
        8. Return a real status: ``completed``, ``failed``, or ``needs-rework``.
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

        # 3-6. Generate, validate, and fix files.
        parser_result, build_result = self._generate_and_validate(
            run_id=context.run_id,
            workspace=workspace_path,
            idea=idea,
            execution_plan=execution_plan,
            architecture=architecture,
            test_report=test_report,
            qa_report=qa_report,
        )

        for relative_path, content in parser_result.files.items():
            write_workspace_file(context.run_id, relative_path, content)
            logs.append(self.log(f"Wrote workspace file {relative_path}"))

        if parser_result.warnings:
            for warning in parser_result.warnings:
                logs.append(self.log(warning, level="warn"))

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

        # Write hygiene files based on detected project type.
        project_type = build_result.project_type if build_result else "unknown"
        hygiene = build_hygiene_files(project_type)
        for relative_path, content in hygiene.to_dict().items():
            write_workspace_file(context.run_id, relative_path, content)
            logs.append(self.log(f"Wrote hygiene file {relative_path}"))

        # 7. Produce the implementation summary artifact.
        workspace_files = list_workspace_files(context.run_id)
        summary = self._build_summary(
            run_id=context.run_id,
            workspace=str(workspace_path),
            idea=idea,
            execution_plan=execution_plan,
            architecture=architecture,
            files=workspace_files,
            parser_result=parser_result,
            build_result=build_result,
        )
        artifact_path = self.artifact_manager.write("execution", summary)
        outputs.append(artifact_path)
        logs.append(self.log(f"Wrote implementation summary to {artifact_path}"))

        # 8. Return status based on validation outcome.
        if build_result and build_result.success:
            status: str = "completed"
            logs.append(self.log("Build and tests passed."))
        elif build_result:
            status = "failed"
            logs.append(
                self.log(
                    f"Build failed after {self.max_fix_iterations} fix iterations.",
                    level="error",
                )
            )
        else:
            # No build result means parsing failed completely.
            status = "failed"
            logs.append(
                self.log(
                    "Could not parse generated files; aborting execution.",
                    level="error",
                )
            )

        return AgentResult(
            status=status,
            outputs=outputs,
            logs=logs,
            artifact_text=summary,
            metadata={"project_type": project_type, "build_success": status == "completed"},
        )

    def _generate_and_validate(
        self,
        *,
        run_id: str,
        workspace: Path,
        idea: str,
        execution_plan: str,
        architecture: str,
        test_report: str,
        qa_report: str,
    ) -> tuple[ParserResult, BuildResult | None]:
        """Generate files and run the build/test/fix loop.

        Returns the final parser result and the final build result. If parsing
        fails on every iteration, the build result is None.
        """
        previous_files: dict[str, str] | None = None
        previous_build: BuildResult | None = None

        for iteration in range(self.max_fix_iterations):
            parser_result = self._generate_code_files(
                run_id=run_id,
                idea=idea,
                execution_plan=execution_plan,
                architecture=architecture,
                test_report=test_report,
                qa_report=qa_report,
                fix_context=previous_build,
                previous_files=previous_files,
                iteration=iteration,
            )

            if not parser_result.files:
                # Parsing produced nothing usable; try once more with the LLM
                # but do not bother running the build.
                previous_build = None
                continue

            # Write the current attempt into the workspace, replacing previous
            # files but keeping hygiene files out of the generated set.
            self._write_parsed_files(run_id, parser_result.files)
            previous_files = dict(parser_result.files)

            # Detect project type from the freshly written files and validate.
            runner = BuildRunner(workspace)
            build_result = runner.validate()

            if build_result.success:
                return parser_result, build_result

            previous_build = build_result

        # Exhausted iterations. Return the last parse/build results we have.
        if previous_build is None:
            # All iterations failed to parse; return the last (empty) parse.
            empty_result = ParserResult(
                error="No parseable files produced after all fix iterations."
            )
            return empty_result, None

        # Return the last parser result (already written) and its build result.
        # Re-parse is cheap; we already have previous_files from the last loop.
        last_parser = ParserResult(files=previous_files or {})
        return last_parser, previous_build

    def _write_parsed_files(self, run_id: str, files: dict[str, str]) -> None:
        """Write parsed files into the workspace, replacing prior content."""
        for relative_path, content in files.items():
            write_workspace_file(run_id, relative_path, content)

    def _generate_code_files(
        self,
        *,
        run_id: str,
        idea: str,
        execution_plan: str,
        architecture: str,
        test_report: str,
        qa_report: str,
        fix_context: BuildResult | None = None,
        previous_files: dict[str, str] | None = None,
        iteration: int = 0,
    ) -> ParserResult:
        """Ask the LLM to produce implementation files and parse the response."""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            run_id=run_id,
            idea=idea,
            execution_plan=execution_plan,
            architecture=architecture,
            test_report=test_report,
            qa_report=qa_report,
            fix_context=fix_context,
            previous_files=previous_files,
            iteration=iteration,
        )

        fallback = self._fallback_code_files(run_id, idea, bool(qa_report))
        response = call_llm("execution", system_prompt, user_prompt, fallback)
        return parse_code_files(response)

    def _build_system_prompt(self) -> str:
        return (
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
            "- Include __init__.py files for Python packages so they are importable.\n"
            "- Prefer self-contained, in-memory or file-based MVPs; avoid external services unless "
            "the architecture explicitly requires them.\n"
            "- If a file contains nested code fences, use four or more backticks for its outer fence.\n"
            "- Keep CLI entry points testable: move logic into importable modules and keep the CLI thin."
        )

    def _build_user_prompt(
        self,
        *,
        run_id: str,
        idea: str,
        execution_plan: str,
        architecture: str,
        test_report: str,
        qa_report: str,
        fix_context: BuildResult | None,
        previous_files: dict[str, str] | None,
        iteration: int,
    ) -> str:
        sections: list[str] = [f"Run ID: {run_id}"]

        sections.extend(
            [
                "## Approved Idea",
                "",
                idea,
                "",
                "## Execution Plan",
                "",
                execution_plan or "_No execution plan provided._",
                "",
                "## Architecture",
                "",
                architecture or "_No architecture design provided._",
            ]
        )

        if qa_report:
            sections.extend(
                [
                    "",
                    "## Previous QA Feedback",
                    "",
                    qa_report,
                    "",
                    "You are running a rework iteration. Address the issues above explicitly. "
                    "Preserve existing tests and only change files necessary to fix the reported defects.",
                ]
            )

        if test_report:
            sections.extend(
                [
                    "",
                    "## Previous Test Report",
                    "",
                    test_report,
                    "",
                    "Fix any reported bugs or gaps where feasible.",
                ]
            )

        if fix_context and not fix_context.success:
            sections.extend(
                [
                    "",
                    "## Build/Test Diagnostics (fix the failures below)",
                    "",
                    fix_context.summary(),
                    "",
                    "Full details:",
                    "",
                    "Install output:",
                    "```",
                    fix_context.install_output,
                    "```",
                    "",
                    "Test output:",
                    "```",
                    fix_context.test_output,
                    "```",
                ]
            )
            if fix_context.typecheck_ok is False:
                sections.extend(
                    [
                        "",
                        "Type-check output:",
                        "```",
                        fix_context.typecheck_output,
                        "```",
                    ]
                )
            if fix_context.lint_ok is False:
                sections.extend(
                    [
                        "",
                        "Lint output:",
                        "```",
                        fix_context.lint_output,
                        "```",
                    ]
                )
            sections.append(
                "\nRegenerate the full file set with the failures above fixed. "
                "Be conservative: keep tests that were passing and fix only the broken parts."
            )

        if previous_files and iteration > 0:
            sections.extend(
                [
                    "",
                    "## Previous File Manifest",
                    "",
                    "The following files were generated in the previous attempt:",
                ]
            )
            for path in sorted(previous_files):
                sections.append(f"- {path}")

        sections.extend(["", "Generate the implementation files now."])
        return "\n".join(sections)

    def _fallback_code_files(self, run_id: str, idea: str, is_rework: bool) -> str:
        """Minimal deterministic fallback if the LLM is unavailable.

        The fallback project is intentionally buildable and testable so the
        pipeline can still run end-to-end without API keys.
        """
        # Python package names cannot contain hyphens or spaces.
        package_name = run_id.replace("-", "_").replace(" ", "_").lower()
        # TOML basic strings cannot contain literal newlines.
        safe_description = idea.replace('"', '\\"').replace('\n', ' ').strip()[:120]
        rework_note = "This is a rework iteration." if is_rework else ""
        return f"""FILE: pyproject.toml
```toml
[project]
name = "{package_name}"
version = "0.1.0"
description = "Autogenerated MVP for: {safe_description}"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = ["pytest"]

[tool.setuptools.packages.find]
where = ["src"]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

FILE: README.md
```markdown
# {run_id}

{idea}

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run tests

```bash
pytest tests/ -q
```

## Notes

This project was generated as a fallback because the LLM was unavailable.
{rework_note}
```

FILE: .gitignore
```gitignore
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.env
.pytest_cache/
.coverage
```

FILE: src/{package_name}/__init__.py
```python
'''Fallback package for {run_id}.'''
```

FILE: src/{package_name}/main.py
```python
'''Fallback main entry point for {run_id}.'''


def main() -> None:
    print("Hello from {run_id}!")
    return None
```

FILE: tests/test_main.py
```python
from {package_name}.main import main


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
        parser_result: ParserResult,
        build_result: BuildResult | None,
    ) -> str:
        file_list = "\n".join(f"- `{f}`" for f in files) or "_No files generated._"

        if build_result:
            build_section = build_result.summary()
            status_line = (
                "**Build status:** passed"
                if build_result.success
                else "**Build status:** failed"
            )
        else:
            build_section = "_No build validation performed._"
            status_line = "**Build status:** unknown"

        warnings_section = ""
        if parser_result.warnings:
            warnings_list = "\n".join(f"- {w}" for w in parser_result.warnings)
            warnings_section = f"\n## Parser Warnings\n\n{warnings_list}\n"

        return f"""# Implementation Summary

**Run:** {run_id}
**Workspace:** `{workspace}`
{status_line}

## What Was Built

Implementation for the approved idea:

> {idea}

## Build & Test Results

{build_section}

## Milestones Completed

Based on the execution plan and architecture design, the following milestones
were targeted:

{execution_plan or "_No execution plan provided._"}

## Architecture Notes

{architecture or "_No architecture design provided._"}

## How to Run

1. Inspect the workspace: `cd {workspace}`
2. Install dependencies and run tests as described in the workspace README.

## Tests Included

- Tests are included in the workspace where applicable; see the Test Agent report
  for independent verification.

## File Manifest

{file_list}
{warnings_section}
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
