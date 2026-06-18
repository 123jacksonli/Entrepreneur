import os
import subprocess

import pytest

from src.agents.test import TestAgent
from src.artifacts import ArtifactManager
from src.config import Config
from src.orchestrator import Orchestrator
from src.state import StateStore
from src.tools.social_trends import SocialTrendClient
from src.tools.web_search import SearchResult


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


def _fake_search_web(query: str, max_results: int = 5):
    return [
        SearchResult(
            title=f"Result for {query}",
            url="https://example.com",
            snippet="Mock search result.",
        )
    ]


def _fake_search_x(self, query: str, max_results: int = 5):
    return []


def _fake_run_pytest(self) -> str:
    return "1 passed in 0.01s"





@pytest.mark.anyio
async def test_orchestrator_runs_full_pipeline(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    outputs_dir = repo / "outputs" / "run-orch"
    workspace_dir = repo / "workspace"
    db_path = repo / "state.db"

    monkeypatch.setattr(Config, "OUTPUTS_DIR", str(outputs_dir))
    monkeypatch.setattr(Config, "WORKSPACE_DIR", str(workspace_dir))
    monkeypatch.setattr(Config, "SQLITE_PATH", str(db_path))
    monkeypatch.chdir(str(repo))

    # Avoid real network, LLM, and recursive pytest calls.
    # Setting the API key to None makes create_completion raise immediately,
    # so agents fall back to their deterministic templates.
    monkeypatch.setattr("src.llm_factory.API_KEY", None)
    for module in ("idea_generation", "research", "plan"):
        monkeypatch.setattr(f"src.agents.{module}.search_web", _fake_search_web)
    monkeypatch.setattr(SocialTrendClient, "search_x", _fake_search_x)
    monkeypatch.setattr(TestAgent, "_run_pytest", _fake_run_pytest)

    state = StateStore(db_path=str(db_path))
    artifacts = ArtifactManager(outputs_dir=str(outputs_dir))
    events: list = []

    orchestrator = Orchestrator(
        state_store=state,
        event_callback=events.append,
        artifact_manager=artifacts,
    )

    await orchestrator.start_run("run-orch", "A test startup idea")

    run = state.get_run("run-orch")
    assert run is not None
    assert run["status"] == "completed"
    assert run["current_agent_id"] == "qa"

    # All artifact files were produced.
    for stage in [
        "00-idea-brief.md",
        "01-research-report.md",
        "02-plan-report.md",
        "03-execution-plan.md",
        "04-architecture-design.md",
        "05-implementation-summary.md",
        "06-test-report.md",
        "07-qa-report.md",
    ]:
        assert (outputs_dir / stage).exists(), f"missing {stage}"

    # The execution branch and workspace were created.
    current_branch = _run_shell("git rev-parse --abbrev-ref HEAD", cwd=str(repo))
    assert current_branch == "exec/run-orch"
    assert (workspace_dir / "run-orch" / "README.md").exists()

    # Key pipeline events were emitted.
    event_types = {e.type for e in events}
    assert "run-started" in event_types
    assert "run-completed" in event_types
    assert "agent-start" in event_types
    assert "agent-complete" in event_types
