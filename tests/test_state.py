import os
import tempfile

import pytest

from src.state import StateStore


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        yield StateStore(db_path=db_path)


def test_create_and_get_run(store):
    store.create_run("run-1", "Idea", "running", "research")
    run = store.get_run("run-1")
    assert run is not None
    assert run["idea"] == "Idea"
    assert run["status"] == "running"
    assert run["current_agent_id"] == "research"


def test_list_runs(store):
    store.create_run("run-1", "Idea 1", "running", "research")
    store.create_run("run-2", "Idea 2", "waiting", "plan")
    runs = store.list_runs()
    assert len(runs) == 2
