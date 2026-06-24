import os
import subprocess

import pytest

from src.tools.git_ops import (
    GitOperationError,
    commit_all,
    get_current_branch,
    get_repo_root,
    has_uncommitted_changes,
)


def _run_shell(cmd: str, cwd: str) -> str:
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _init_git_repo(path: str) -> None:
    path = str(path)
    _run_shell("git init -b main", cwd=path)
    _run_shell('git config user.email "test@example.com"', cwd=path)
    _run_shell('git config user.name "Test User"', cwd=path)

    readme = os.path.join(path, "README.md")
    with open(readme, "w") as f:
        f.write("# test repo\n")
    _run_shell("git add README.md", cwd=path)
    _run_shell('git commit -m "initial"', cwd=path)


def test_get_repo_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    assert get_repo_root(str(repo)) == str(repo)


def test_get_current_branch(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    assert get_current_branch(str(repo)) == "main"


def test_commit_all_refuses_protected_branch(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    with open(os.path.join(repo, "bad.txt"), "w") as f:
        f.write("nope")

    with pytest.raises(GitOperationError, match="Refusing to commit"):
        commit_all("bad commit", repo_path=str(repo))


def test_has_uncommitted_changes(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    assert not has_uncommitted_changes(str(repo))
    with open(os.path.join(repo, "new.txt"), "w") as f:
        f.write("change")
    assert has_uncommitted_changes(str(repo))
