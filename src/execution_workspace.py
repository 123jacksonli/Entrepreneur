"""Isolated workspace helpers for Execution Agent runs.

Each run gets its own directory under ``workspace/{run_id}/`` so that multiple
runs or iterations can be developed and tested without overwriting each other.
The workspace is committed to the run branch along with the implementation
summary.

For startup-only branches, files are also written to a git worktree root so the
run branch contains only the generated startup code.
"""

from pathlib import Path

from src.config import Config

# Patterns that should never be copied from the workspace to the run branch.
_EXCLUDED_PARTS = {
    ".pytest_cache",
    "__pycache__",
    ".egg-info",
    ".eggs",
    "build",
    "dist",
    ".coverage",
    "htmlcov",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
}


def _is_excluded(path: Path) -> bool:
    """Return True if the path matches a build/cache artifact pattern."""
    parts = path.parts
    if any(part in _EXCLUDED_PARTS for part in parts):
        return True
    # Exclude directories whose name ends with `.egg-info` anywhere in the tree.
    return any(part.endswith(".egg-info") for part in parts)


def get_workspace_path(run_id: str) -> Path:
    """Return the workspace directory path for a run."""
    return Path(Config.WORKSPACE_DIR) / run_id


def prepare_workspace(run_id: str) -> Path:
    """Create the workspace directory for a run and return its path."""
    path = get_workspace_path(run_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_workspace_file(run_id: str, relative_path: str, content: str) -> Path:
    """Write ``content`` to a file inside the run workspace."""
    workspace = prepare_workspace(run_id)
    file_path = workspace / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def read_workspace_file(run_id: str, relative_path: str) -> str:
    """Read ``relative_path`` from the run workspace as text."""
    file_path = get_workspace_path(run_id) / relative_path
    return file_path.read_text(encoding="utf-8")


def list_workspace_files(run_id: str) -> list[str]:
    """Return all file paths inside the run workspace, relative to the workspace root."""
    workspace = prepare_workspace(run_id)
    files: list[str] = []
    for path in workspace.rglob("*"):
        if path.is_file() and not _is_excluded(path):
            files.append(str(path.relative_to(workspace)))
    return sorted(files)


def write_worktree_file(worktree_path: Path, relative_path: str, content: str) -> Path:
    """Write ``content`` to a file inside a git worktree root."""
    file_path = worktree_path / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def list_worktree_files(worktree_path: Path) -> list[str]:
    """Return all file paths inside a worktree root, relative to the root."""
    files: list[str] = []
    if not worktree_path.exists():
        return files
    for path in worktree_path.rglob("*"):
        if path.is_file() and not _is_excluded(path):
            files.append(str(path.relative_to(worktree_path)))
    return sorted(files)


def copy_workspace_to_worktree(run_id: str, worktree_path: Path) -> None:
    """Copy implementation files from the run workspace into the worktree root.

    Build artifacts, caches, and VCS metadata are excluded so the run branch
    contains only the generated startup code.
    """
    workspace = prepare_workspace(run_id)
    if not workspace.exists():
        return
    for src in workspace.rglob("*"):
        if src.is_file() and not _is_excluded(src):
            dst = worktree_path / src.relative_to(workspace)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))


# Import shutil here to avoid importing at module top while still being available.
import shutil  # noqa: E402
