"""Git operations for the Execution Agent.

Supports two modes:
1. GitHub MCP (preferred) — creates branches, commits, and pushes via MCP tools.
2. git CLI fallback — uses local git when MCP is unavailable.

The Execution Agent creates a new branch for every run so that code changes are
isolated from `main` until the run completes and passes QA.
"""

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any

from src.config import Config

logger = logging.getLogger(__name__)


class GitOperationError(Exception):
    """Raised when a git command fails."""


@dataclass
class CommitResult:
    branch: str
    commit_hash: str
    remote_url: str
    branch_url: str | None = None


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
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
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


def run_branch_name(run_id: str) -> str:
    """Return the execution branch name for a run."""
    prefix = Config.EXEC_BRANCH_PREFIX
    return f"{prefix}/{run_id}"


def _protected_branches() -> set[str]:
    return {"main", "master", "develop", "dev"}


def _guard_protected_branch(branch_name: str) -> None:
    """Prevent accidental commits to protected default branches."""
    if branch_name in _protected_branches():
        raise GitOperationError(
            f"Refusing to commit to protected branch '{branch_name}'. "
            "Create a run branch first."
        )


def _remote_default_branch(repo_path: str | None = None) -> str:
    """Return origin's default branch if available, otherwise local HEAD."""
    try:
        result = _run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo_path)
        return result.stdout.strip().rsplit("/", 1)[-1]
    except GitOperationError:
        return get_default_branch(repo_path)


def create_run_branch(run_id: str, repo_path: str | None = None) -> str:
    """Create and check out a dedicated branch for a run.

    The branch is created from the latest origin default branch so each run
    starts from a clean, up-to-date baseline.
    """
    cwd = repo_path or get_repo_root()
    branch_name = run_branch_name(run_id)
    default = _remote_default_branch(cwd)

    try:
        _run_git(["fetch", "origin", default], cwd=cwd)
        _run_git(["checkout", "-B", branch_name, f"origin/{default}"], cwd=cwd)
    except GitOperationError:
        logger.warning(
            "Could not create branch from origin/%s; falling back to local HEAD", default
        )
        _run_git(["checkout", "-B", branch_name], cwd=cwd)

    logger.info("Created and checked out run branch %s", branch_name)
    return branch_name


def ensure_run_branch(run_id: str, repo_path: str | None = None) -> str:
    """Check out the run branch, creating it if necessary."""
    cwd = repo_path or get_repo_root()
    branch_name = run_branch_name(run_id)
    current = get_current_branch(cwd)
    if current == branch_name:
        return branch_name

    try:
        _run_git(["rev-parse", "--verify", branch_name], cwd=cwd)
        _run_git(["checkout", branch_name], cwd=cwd)
    except GitOperationError:
        create_run_branch(run_id, repo_path=cwd)

    return branch_name


def commit_all(
    message: str,
    repo_path: str | None = None,
    paths: list[str] | None = None,
) -> str:
    """Stage and commit changes. Returns the commit hash."""
    cwd = repo_path or get_repo_root()
    current = get_current_branch(cwd)
    _guard_protected_branch(current)

    if paths:
        for path in paths:
            _run_git(["add", path], cwd=cwd)
    else:
        _run_git(["add", "-A"], cwd=cwd)

    # Only commit if there is something to commit.
    status = _run_git(["status", "--porcelain"], cwd=cwd)
    if not status.stdout.strip():
        logger.info("No changes to commit on %s", current)
        return _run_git(["rev-parse", "HEAD"], cwd=cwd).stdout.strip()

    _run_git(["commit", "-m", message], cwd=cwd)
    commit_hash = _run_git(["rev-parse", "HEAD"], cwd=cwd).stdout.strip()
    logger.info("Committed %s on %s: %s", commit_hash[:8], current, message)
    return commit_hash


def push_run_branch(run_id: str, repo_path: str | None = None) -> str:
    """Push the run branch to origin and return the remote URL.

    If ``GITHUB_PERSONAL_ACCESS_TOKEN`` is set and the origin remote is an
    HTTPS GitHub URL, the token is embedded so the push can run without an
    interactive credential prompt.
    """
    cwd = repo_path or get_repo_root()
    branch_name = run_branch_name(run_id)
    remote_url = _run_git(["remote", "get-url", "origin"], cwd=cwd).stdout.strip()

    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    owner_repo = _parse_github_owner_repo(remote_url)
    if token and owner_repo and remote_url.startswith("https://"):
        auth_url = f"https://{token}@github.com/{owner_repo[0]}/{owner_repo[1]}.git"
        _run_git(["push", auth_url, branch_name], cwd=cwd)
        try:
            _run_git(
                ["branch", "--set-upstream-to", f"origin/{branch_name}", branch_name],
                cwd=cwd,
            )
        except GitOperationError:
            pass
    else:
        _run_git(["push", "-u", "origin", branch_name], cwd=cwd)

    logger.info("Pushed %s to origin", branch_name)
    return remote_url


def _parse_github_owner_repo(remote_url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub remote URL."""
    patterns = [
        r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
        r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, remote_url)
        if match:
            return match.group("owner"), match.group("repo")
    return None


def _github_branch_url(owner: str, repo: str, branch: str) -> str:
    return f"https://github.com/{owner}/{repo}/tree/{branch}"


def commit_milestone(
    run_id: str,
    message: str,
    repo_path: str | None = None,
    paths: list[str] | None = None,
    push: bool = True,
) -> CommitResult:
    """Ensure the run branch is checked out, commit changes, and optionally push.

    This is the main entry point used by the Execution Agent after each
    completed milestone.
    """
    cwd = repo_path or get_repo_root()
    branch_name = ensure_run_branch(run_id, repo_path=cwd)
    _guard_protected_branch(branch_name)

    commit_hash = commit_all(message, repo_path=cwd, paths=paths)
    remote_url = ""
    branch_url: str | None = None

    if push:
        try:
            remote_url = push_run_branch(run_id, repo_path=cwd)
            owner_repo = _parse_github_owner_repo(remote_url)
            if owner_repo:
                branch_url = _github_branch_url(*owner_repo, branch_name)
        except GitOperationError as exc:
            logger.warning("Failed to push milestone commit: %s", exc)

    return CommitResult(
        branch=branch_name,
        commit_hash=commit_hash,
        remote_url=remote_url,
        branch_url=branch_url,
    )


# ---------------------------------------------------------------------------
# GitHub MCP helpers
# ---------------------------------------------------------------------------

# NOTE: These functions assume the GitHub MCP tools are available in the
# execution environment. They return payloads that the orchestrator can pass
# directly to the MCP tools.


def mcp_create_branch(
    owner: str,
    repo: str,
    run_id: str,
    from_branch: str = "main",
) -> dict[str, Any]:
    """Return parameters for the GitHub MCP create_branch tool."""
    return {
        "owner": owner,
        "repo": repo,
        "branch": run_branch_name(run_id),
        "from_branch": from_branch,
    }


def mcp_push_files(
    owner: str,
    repo: str,
    run_id: str,
    message: str,
    files: list[dict[str, str]],
) -> dict[str, Any]:
    """Return parameters for the GitHub MCP push_files tool."""
    return {
        "owner": owner,
        "repo": repo,
        "branch": run_branch_name(run_id),
        "message": message,
        "files": files,
    }


def mcp_owner_repo_from_remote(repo_path: str | None = None) -> tuple[str, str] | None:
    """Parse owner/repo from the origin remote for use with MCP tools."""
    try:
        remote_url = _run_git(
            ["remote", "get-url", "origin"], cwd=repo_path
        ).stdout.strip()
    except GitOperationError:
        return None
    return _parse_github_owner_repo(remote_url)
