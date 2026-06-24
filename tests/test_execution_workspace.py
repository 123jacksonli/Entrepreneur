"""Tests for execution workspace helpers."""

from pathlib import Path

import pytest

from src.agents.execution import ExecutionAgent
from src.config import Config
from src.execution_workspace import _is_excluded, list_workspace_files


class TestParseCodeFiles:
    def test_parse_single_file(self):
        agent = ExecutionAgent()
        text = (
            "FILE: src/main.py\n"
            "```python\n"
            "def main():\n"
            "    pass\n"
            "```\n"
        )
        files = agent._parse_code_files(text)
        assert files == {"src/main.py": "def main():\n    pass"}

    def test_parse_empty_file(self):
        agent = ExecutionAgent()
        text = (
            "FILE: tests/__init__.py\n"
            "```python\n"
            "\n"
            "```\n"
            "\n"
            "FILE: tests/test_foo.py\n"
            "```python\n"
            "def test_foo():\n"
            "    assert True\n"
            "```\n"
        )
        files = agent._parse_code_files(text)
        assert "tests/__init__.py" in files
        assert files["tests/__init__.py"] == ""
        assert "def test_foo()" in files["tests/test_foo.py"]

    def test_parse_file_with_nested_backticks(self):
        agent = ExecutionAgent()
        text = (
            "FILE: readme.md\n"
            "```markdown\n"
            "Example:\n"
            "```python\n"
            "x = 1\n"
            "```\n"
            "```\n"
        )
        files = agent._parse_code_files(text)
        assert "readme.md" in files
        assert "```python" in files["readme.md"]
        assert "x = 1" in files["readme.md"]


class TestIsExcluded:
    @pytest.mark.parametrize(
        "relative_path,expected",
        [
            ("__pycache__/foo.cpython-314.pyc", True),
            ("tests/__pycache__/test_foo.cpython-314.pyc", True),
            (".pytest_cache/v/cache/nodeids", True),
            ("src/passgen.egg-info/PKG-INFO", True),
            ("build/lib/foo.py", True),
            ("dist/foo-0.1.0.tar.gz", True),
            ("src/main.py", False),
            ("tests/test_foo.py", False),
            (".gitignore", False),
        ],
    )
    def test_is_excluded(self, relative_path, expected):
        path = Path(relative_path)
        assert _is_excluded(path) is expected


class TestListWorkspaceFiles:
    def test_lists_files_and_excludes_artifacts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "WORKSPACE_DIR", str(tmp_path / "workspace"))
        workspace = tmp_path / "workspace" / "run-1"
        workspace.mkdir(parents=True)
        (workspace / "src" / "main.py").parent.mkdir(parents=True)
        (workspace / "src" / "main.py").write_text("x = 1")
        (workspace / "__pycache__" / "main.cpython-314.pyc").parent.mkdir(parents=True)
        (workspace / "__pycache__" / "main.cpython-314.pyc").write_text("cache")

        files = list_workspace_files("run-1")
        assert files == ["src/main.py"]
