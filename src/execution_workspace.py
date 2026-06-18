"""Isolated workspace helpers for Execution Agent runs.

Each run gets its own directory under ``workspace/{run_id}/`` so that multiple
runs or iterations can be developed and tested without overwriting each other.
The workspace is committed to the run branch along with the implementation
summary.
"""

from pathlib import Path

from src.config import Config


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
