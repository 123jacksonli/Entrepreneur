"""Tests for the Execution Agent self-healing fix loop."""

import pytest

from src.agents.base import AgentContext
from src.agents.execution import ExecutionAgent
from src.artifacts import ArtifactManager
from src.config import Config


_BROKEN_PYTHON_PROJECT = """
FILE: pyproject.toml
```toml
[project]
name = "demo"
version = "0.1.0"
dependencies = []

[project.optional-dependencies]
dev = ["pytest"]

[tool.setuptools.packages.find]
where = ["src"]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

FILE: src/demo/__init__.py
```python
```

FILE: src/demo/main.py
```python
def add(a, b):
    return a - b  # bug: subtraction instead of addition
```

FILE: tests/test_main.py
```python
from demo.main import add

def test_add():
    assert add(2, 3) == 5
```
"""

_FIXED_PYTHON_PROJECT = """
FILE: pyproject.toml
```toml
[project]
name = "demo"
version = "0.1.0"
dependencies = []

[project.optional-dependencies]
dev = ["pytest"]

[tool.setuptools.packages.find]
where = ["src"]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

FILE: src/demo/__init__.py
```python
```

FILE: src/demo/main.py
```python
def add(a, b):
    return a + b
```

FILE: tests/test_main.py
```python
from demo.main import add

def test_add():
    assert add(2, 3) == 5
```
"""


@pytest.mark.anyio
async def test_execution_agent_fixes_broken_code(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    workspace_root = repo / "workspace"
    outputs_dir = repo / "outputs"
    monkeypatch.setattr(Config, "WORKSPACE_DIR", str(workspace_root))
    monkeypatch.setattr(Config, "OUTPUTS_DIR", str(outputs_dir))
    monkeypatch.chdir(str(repo))

    call_count = 0

    def _mock_call_llm(agent_id, system_prompt, user_prompt, fallback):
        nonlocal call_count
        call_count += 1
        # First call returns broken code; second call returns the fix.
        return _BROKEN_PYTHON_PROJECT if call_count == 1 else _FIXED_PYTHON_PROJECT

    monkeypatch.setattr("src.agents.execution.call_llm", _mock_call_llm)

    agent = ExecutionAgent(
        artifact_manager=ArtifactManager(run_id="run-fix"),
        max_fix_iterations=2,
    )
    context = AgentContext(run_id="run-fix", idea="A demo adder")
    result = await agent.run(context)

    assert result.status == "completed"
    assert call_count == 2
    assert (workspace_root / "run-fix" / "src" / "demo" / "main.py").exists()
    main_content = (workspace_root / "run-fix" / "src" / "demo" / "main.py").read_text()
    assert "a + b" in main_content
