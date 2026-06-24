"""Focused test #2: password generator CLI (no external deps), workspace-only."""

import asyncio
import shutil
import sys
import traceback
from pathlib import Path

from src.agents.base import AgentContext
from src.agents.execution import ExecutionAgent
from src.agents.qa import QAAgent
from src.agents.test import TestAgent
from src.artifacts import ArtifactManager
from src.config import Config
from src.llm_factory import create_completion

RUN_ID = "exec-test-run-2"


def _extract_verdict(text: str) -> str | None:
    import re

    m = re.search(r"Verdict:\s*(accept|conditional accept|reject)", text, re.IGNORECASE)
    return m.group(1).lower() if m else None


_orig_create_completion = create_completion


def _timed_create_completion(agent_id, system_prompt, user_prompt, **kwargs):
    kwargs.setdefault("timeout", 300)
    return _orig_create_completion(agent_id, system_prompt, user_prompt, **kwargs)


import src.agents._utils
import src.llm_factory

src.agents._utils.create_completion = _timed_create_completion
src.llm_factory.create_completion = _timed_create_completion


async def main() -> None:
    Config.OUTPUTS_DIR = "outputs/exec-test"
    am = ArtifactManager(outputs_dir=Config.OUTPUTS_DIR, run_id=RUN_ID)

    prev_workspace = Path(Config.WORKSPACE_DIR) / RUN_ID
    if prev_workspace.exists():
        shutil.rmtree(prev_workspace, ignore_errors=True)

    idea = "A minimal Python CLI tool that generates secure random passwords with configurable length and character sets."

    execution_plan = """# Execution Plan

Build a minimal, working Python CLI that generates secure random passwords.

## Milestones
1. CLI argument parsing (length, include digits, symbols, uppercase).
2. Secure random password generation using Python's standard library.
3. Validation of minimum length and character-set constraints.
4. Unit tests covering length, character sets, and edge cases.
5. README with install and usage instructions.

## Definition of Done
- `python -m pytest` passes.
- `python -m passgen --length 16` produces a 16-character password.
"""

    architecture = """# Architecture

- Language: Python 3.11+
- CLI: `argparse`
- Random source: `secrets` module from the Python standard library
- Packaging: `pyproject.toml`
- Tests: `pytest`
- No external dependencies beyond Python stdlib and pytest.
"""

    ctx = AgentContext(
        run_id=RUN_ID,
        idea=idea,
        artifacts={
            "idea-generation": idea,
            "execution-plan": execution_plan,
            "architecture": architecture,
        },
    )

    max_iterations = 5
    for iteration in range(1, max_iterations + 1):
        print(f"\n{'#' * 78}")
        print(f"# QA LOOP ITERATION {iteration}")
        print("#" * 78)

        print("\n>>> Running Execution Agent...")
        exec_agent = ExecutionAgent(artifact_manager=am)
        exec_result = await exec_agent.run(ctx)
        ctx.artifacts["execution"] = exec_result.artifact_text

        workspace = Path(Config.WORKSPACE_DIR) / RUN_ID
        files = sorted(
            str(p.relative_to(workspace))
            for p in workspace.rglob("*")
            if p.is_file()
        )
        print(f"Workspace: {workspace}")
        print("Files in workspace:\n", "\n".join(files))

        print("\n>>> Running Test Agent...")
        test_agent = TestAgent(artifact_manager=am)
        test_result = await test_agent.run(ctx)
        ctx.artifacts["test"] = test_result.artifact_text
        print("\n--- Test report ---\n", test_result.artifact_text[:2000])

        print("\n>>> Running QA Agent...")
        qa_agent = QAAgent(artifact_manager=am)
        qa_result = await qa_agent.run(ctx)
        ctx.artifacts["qa"] = qa_result.artifact_text
        verdict = qa_result.metadata.get("verdict") if qa_result.metadata else None
        if verdict is None:
            verdict = _extract_verdict(qa_result.artifact_text)
        print(f"[QA VERDICT] {verdict}")

        if verdict in ("accept", "conditional accept"):
            print("\n[SUCCESS] QA accepted the implementation.")
            break

        print("\n[REJECTED] Re-running Execution Agent with QA feedback...")
    else:
        print("\n[EXHAUSTED] Max iterations reached without QA acceptance.")

    print(f"\n{'=' * 78}")
    print(f"Workspace: workspace/{RUN_ID}/")
    print(f"Artifacts: {Config.OUTPUTS_DIR}/{RUN_ID}/")
    print("=" * 78)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
