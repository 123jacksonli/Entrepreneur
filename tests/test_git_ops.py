import os
import subprocess

import pytest

from src.config import Config
from src.tools.git_ops import (
    CommitResult,
    GitOperationError,
    commit_all,
    commit_milestone,
    create_run_branch,
    ensure_run_branch,
    get_current_branch,
    get_repo_root,
    has_uncommitted_changes,
    mcp_create_branch,
    mcp_owner_repo_from_remote,
    push_run_branch,
    run_branch_name,
)


def _run_shell(cmd: str, cwd: str) -> str:
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _init_git_repo(path: str, with_remote: bool = True) -> str:
    path = str(path)
    _run_shell("git init -b main", cwd=path)
    _run_shell('git config user.email "test@example.com"', cwd=path)
    _run_shell('git config user.name "Test User"', cwd=path)

    readme = os.path.join(path, "README.md")
    with open(readme, "w") as f:
        f.write("# test repo\n")
    _run_shell("git add README.md", cwd=path)
    _run_shell('git commit -m "initial"', cwd=path)

    if with_remote:
        bare_path = os.path.join(path, "origin.git")
        _run_shell(f"git init --bare origin.git", cwd=path)
        _run_shell(f"git remote add origin {bare_path}", cwd=path)
        _run_shell("git push -u origin main", cwd=path)
        return bare_path
    return ""


@pytest.fixture
def exec_prefix(monkeypatch):
    monkeypatch.setattr(Config, "EXEC_BRANCH_PREFIX", "test-exec")
    return "test-exec"


def test_run_branch_name(exec_prefix):
    assert run_branch_name("run-123") == "test-exec/run-123"


def test_get_repo_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo, with_remote=False)
    assert get_repo_root(str(repo)) == str(repo)


def test_create_run_branch(tmp_path, exec_prefix):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    branch = create_run_branch("run-42", repo_path=str(repo))
    assert branch == "test-exec/run-42"
    assert get_current_branch(str(repo)) == branch


def test_ensure_run_branch_checks_out_existing(tmp_path, exec_prefix):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    create_run_branch("run-7", repo_path=str(repo))
    _run_shell("git checkout main", cwd=str(repo))

    branch = ensure_run_branch("run-7", repo_path=str(repo))
    assert branch == "test-exec/run-7"
    assert get_current_branch(str(repo)) == branch


def test_commit_milestone_stages_commits_and_pushes(tmp_path, exec_prefix):
    repo = tmp_path / "repo"
    repo.mkdir()
    bare_path = _init_git_repo(repo)
    create_run_branch("run-99", repo_path=str(repo))

    code_file = os.path.join(repo, "feature.py")
    with open(code_file, "w") as f:
        f.write("print('hello')\n")

    result = commit_milestone(
        "run-99", "feat: add hello feature", repo_path=str(repo)
    )

    assert isinstance(result, CommitResult)
    assert result.branch == "test-exec/run-99"
    assert len(result.commit_hash) == 40
    assert bare_path in result.remote_url or result.remote_url.endswith("origin.git")

    # Verify the commit exists on the bare remote.
    remote_branches = _run_shell(
        f"git --git-dir={bare_path} for-each-ref --format='%(refname:short)' refs/heads/",
        cwd=str(tmp_path),
    )
    assert "test-exec/run-99" in remote_branches


def test_commit_milestone_without_push(tmp_path, exec_prefix):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo, with_remote=False)
    create_run_branch("run-1", repo_path=str(repo))

    with open(os.path.join(repo, "file.txt"), "w") as f:
        f.write("data")

    result = commit_milestone(
        "run-1", "chore: add file", repo_path=str(repo), push=False
    )
    assert result.branch == "test-exec/run-1"
    assert result.remote_url == ""


def test_commit_all_refuses_protected_branch(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo, with_remote=False)

    with open(os.path.join(repo, "bad.txt"), "w") as f:
        f.write("nope")

    with pytest.raises(GitOperationError, match="Refusing to commit"):
        commit_all("bad commit", repo_path=str(repo))


def test_has_uncommitted_changes(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo, with_remote=False)

    assert not has_uncommitted_changes(str(repo))
    with open(os.path.join(repo, "new.txt"), "w") as f:
        f.write("change")
    assert has_uncommitted_changes(str(repo))


def test_push_run_branch_without_remote_raises(tmp_path, exec_prefix):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo, with_remote=False)
    create_run_branch("run-5", repo_path=str(repo))

    with pytest.raises(GitOperationError):
        push_run_branch("run-5", repo_path=str(repo))


def test_mcp_create_branch_payload(exec_prefix):
    payload = mcp_create_branch("owner", "repo", "run-abc", from_branch="main")
    assert payload["owner"] == "owner"
    assert payload["repo"] == "repo"
    assert payload["branch"] == "test-exec/run-abc"
    assert payload["from_branch"] == "main"


def test_mcp_owner_repo_from_remote(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo, with_remote=False)
    _run_shell(
        "git remote add origin https://github.com/owner-name/repo-name.git",
        cwd=str(repo),
    )
    owner_repo = mcp_owner_repo_from_remote(str(repo))
    assert owner_repo == ("owner-name", "repo-name")
