"""Basic git helpers used by the codebase.

This module no longer manages per-run branches or worktrees. The Execution
Agent now writes all generated files directly to an isolated workspace folder
under ``workspace/{run_id}/``.
"""

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class GitOperationError(Exception):
    """Raised when a git command fails."""


def _run_git(
    args: list[str],
    cwd: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a git command and return the completed process."""
    cmd = ["git", *args]
    logger.debug("Running git command: %s (cwd=%s)", " ".join(cmd), cwd or os.getcwd())
    result = subprocess.run(
        cmd,
        cwd=cwd or os.getcwd(),
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise GitOperationError(
            f"git {' '.join(args)} failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result


def get_repo_root(cwd: str | None = None) -> str:
    """Return the absolute path to the repository root."""
    result = _run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    return result.stdout.strip()


def get_current_branch(repo_path: str | None = None) -> str:
    """Return the current branch name, or HEAD if detached."""
    try:
        result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        branch = result.stdout.strip()
        if branch != "HEAD":
            return branch
    except GitOperationError:
        pass
    result = _run_git(["branch", "--show-current"], cwd=repo_path)
    return result.stdout.strip()


def get_default_branch(repo_path: str | None = None) -> str:
    """Return the default branch name (main or master)."""
    try:
        return get_current_branch(repo_path)
    except GitOperationError:
        return "main"


def has_uncommitted_changes(repo_path: str | None = None) -> bool:
    """Return True if the working tree has staged or unstaged changes."""
    result = _run_git(["status", "--porcelain"], cwd=repo_path)
    return bool(result.stdout.strip())


def _protected_branches() -> set[str]:
    return {"main", "master", "develop", "dev"}


def _guard_protected_branch(branch_name: str) -> None:
    """Prevent accidental commits to protected default branches."""
    if branch_name in _protected_branches():
        raise GitOperationError(
            f"Refusing to commit to protected branch '{branch_name}'. "
            "Create a feature branch first."
        )


def commit_all(
    message: str,
    repo_path: str | None = None,
    paths: list[str] | None = None,
) -> str:
    """Stage and commit changes in the current repository. Returns the commit hash."""
    cwd = repo_path or get_repo_root()
    current = get_current_branch(cwd)
    _guard_protected_branch(current)

    if paths:
        for path in paths:
            _run_git(["add", "-f", path], cwd=cwd)
    else:
        _run_git(["add", "-Af"], cwd=cwd)

    status = _run_git(["status", "--porcelain"], cwd=cwd)
    if not status.stdout.strip():
        logger.info("No changes to commit on %s", current)
        return _run_git(["rev-parse", "HEAD"], cwd=cwd).stdout.strip()

    _run_git(["commit", "-m", message], cwd=cwd)
    commit_hash = _run_git(["rev-parse", "HEAD"], cwd=cwd).stdout.strip()
    logger.info("Committed %s on %s: %s", commit_hash[:8], current, message)
    return commit_hash
