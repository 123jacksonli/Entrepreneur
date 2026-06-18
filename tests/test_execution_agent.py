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

    # Keep the run workspace inside the repo so it can be committed to the
    # run branch, but outside the source/output paths used by other runs.
    workspace_root = repo / "workspace"
    monkeypatch.setattr(Config, "WORKSPACE_DIR", str(workspace_root))

    # Run from inside the temp repository so git_ops resolves the repo root.
    monkeypatch.chdir(str(repo))

    agent = ExecutionAgent(artifact_manager=ArtifactManager(run_id="run-exec"))
    context = AgentContext(run_id="run-exec", idea="A test startup idea")
    result = await agent.run(context)

    assert result.status == "completed"
    assert any("05-implementation-summary.md" in o for o in result.outputs)

    # Branch was created and checked out.
    current_branch = _run_shell("git rev-parse --abbrev-ref HEAD", cwd=str(repo))
    assert current_branch == "exec/run-exec"

    # The implementation summary file exists and is tracked.
    summary_path = repo / "outputs" / "run-exec" / "05-implementation-summary.md"
    assert summary_path.exists()
    content = summary_path.read_text()
    assert "run-exec" in content
    assert "A test startup idea" in content
    assert str(workspace_root / "run-exec") in content

    # A dedicated workspace directory was created for this run.
    run_workspace = workspace_root / "run-exec"
    assert run_workspace.exists()
    workspace_readme = run_workspace / "README.md"
    assert workspace_readme.exists()
    assert "run-exec" in workspace_readme.read_text()

    # The milestone was pushed to the bare remote.
    remote_branches = _run_shell(
        f"git --git-dir={bare_path} for-each-ref --format='%(refname:short)' refs/heads/",
        cwd=str(tmp_path),
    )
    assert "exec/run-exec" in remote_branches

    # The workspace content is in the remote commit tree.
    ls_tree = _run_shell(
        f"git --git-dir={bare_path} ls-tree -r exec/run-exec --name-only",
        cwd=str(tmp_path),
    )
    assert "workspace/run-exec/README.md" in ls_tree
    assert "outputs/run-exec/05-implementation-summary.md" in ls_tree
