import os
import subprocess

import pytest

from src.agents.base import AgentContext
from src.agents.execution import ExecutionAgent
from src.artifacts import ArtifactManager
from src.config import Config


def _run_shell(cmd: str, cwd: str) -> str:
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


@pytest.mark.anyio
async def test_execution_agent_creates_workspace(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize a git repo so git_ops helpers used elsewhere stay happy.
    _run_shell("git init -b main", cwd=str(repo))
    _run_shell('git config user.email "test@example.com"', cwd=str(repo))
    _run_shell('git config user.name "Test User"', cwd=str(repo))
    readme = repo / "README.md"
    readme.write_text("# test repo\n")
    _run_shell("git add README.md", cwd=str(repo))
    _run_shell('git commit -m "initial"', cwd=str(repo))

    workspace_root = repo / "workspace"
    monkeypatch.setattr(Config, "WORKSPACE_DIR", str(workspace_root))
    monkeypatch.chdir(str(repo))

    agent = ExecutionAgent(artifact_manager=ArtifactManager(run_id="run-exec"))
    context = AgentContext(run_id="run-exec", idea="A test startup idea")
    result = await agent.run(context)

    assert result.status == "completed"
    assert any("05-implementation-summary.md" in o for o in result.outputs)

    # Main repo branch should be unchanged.
    current_branch = _run_shell("git rev-parse --abbrev-ref HEAD", cwd=str(repo))
    assert current_branch == "main"

    # A dedicated workspace directory was created for this run.
    run_workspace = workspace_root / "run-exec"
    assert run_workspace.exists()
    workspace_readme = run_workspace / "README.md"
    assert workspace_readme.exists()
    assert "run-exec" in workspace_readme.read_text()

    # The implementation summary file exists.
    summary_path = repo / "outputs" / "run-exec" / "05-implementation-summary.md"
    assert summary_path.exists()
    content = summary_path.read_text()
    assert "run-exec" in content
    assert "A test startup idea" in content
    assert str(run_workspace) in content
