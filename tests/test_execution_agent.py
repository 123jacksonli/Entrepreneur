import os
import subprocess

import pytest

from src.agents.base import AgentContext
from src.agents.execution import ExecutionAgent


def _run_shell(cmd: str, cwd: str) -> str:
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _init_git_repo(path: str) -> str:
    path = str(path)
    _run_shell("git init -b main", cwd=path)
    _run_shell('git config user.email "test@example.com"', cwd=path)
    _run_shell('git config user.name "Test User"', cwd=path)
    readme = os.path.join(path, "README.md")
    with open(readme, "w") as f:
        f.write("# test repo\n")
    _run_shell("git add README.md", cwd=path)
    _run_shell('git commit -m "initial"', cwd=path)

    bare_path = os.path.join(path, "origin.git")
    _run_shell("git init --bare origin.git", cwd=path)
    _run_shell(f"git remote add origin {bare_path}", cwd=path)
    _run_shell("git push -u origin main", cwd=path)
    return bare_path


@pytest.mark.anyio
async def test_execution_agent_creates_branch_and_commits(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    bare_path = _init_git_repo(repo)

    # Run from inside the temp repository so git_ops resolves the repo root.
    monkeypatch.chdir(str(repo))

    agent = ExecutionAgent()
    context = AgentContext(run_id="run-exec", idea="A test startup idea")
    result = await agent.run(context)

    assert result.status == "completed"
    assert any("outputs/05-implementation-summary.md" in o for o in result.outputs)

    # Branch was created and checked out.
    current_branch = _run_shell("git rev-parse --abbrev-ref HEAD", cwd=str(repo))
    assert current_branch == "exec/run-exec"

    # The implementation summary file exists and is tracked.
    summary_path = repo / "outputs" / "05-implementation-summary.md"
    assert summary_path.exists()
    content = summary_path.read_text()
    assert "run-exec" in content
    assert "A test startup idea" in content

    # The milestone was pushed to the bare remote.
    remote_branches = _run_shell(
        f"git --git-dir={bare_path} for-each-ref --format='%(refname:short)' refs/heads/",
        cwd=str(tmp_path),
    )
    assert "exec/run-exec" in remote_branches
