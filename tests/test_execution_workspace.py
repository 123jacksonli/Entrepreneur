"""Tests for execution workspace helpers and the file parser."""

from pathlib import Path

import pytest

from src.config import Config
from src.execution_parser import parse_code_files
from src.execution_workspace import _is_excluded, list_workspace_files


class TestParseCodeFiles:
    def test_parse_single_file(self):
        text = (
            "FILE: src/main.py\n"
            "```python\n"
            "def main():\n"
            "    pass\n"
            "```\n"
        )
        files = parse_code_files(text)
        assert files.files == {"src/main.py": "def main():\n    pass"}

    def test_parse_empty_file(self):
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
        result = parse_code_files(text)
        assert "tests/__init__.py" in result.files
        assert result.files["tests/__init__.py"] == ""
        assert "def test_foo()" in result.files["tests/test_foo.py"]

    def test_parse_file_with_nested_backticks(self):
        text = (
            "FILE: readme.md\n"
            "```markdown\n"
            "Example:\n"
            "```python\n"
            "x = 1\n"
            "```\n"
            "```\n"
        )
        result = parse_code_files(text)
        assert "readme.md" in result.files
        assert "```python" in result.files["readme.md"]
        assert "x = 1" in result.files["readme.md"]

    def test_parse_rejects_absolute_and_traversal_paths(self):
        text = (
            "FILE: /etc/passwd\n"
            "```text\n"
            "root\n"
            "```\n"
            "FILE: ../../escape.py\n"
            "```python\n"
            "print('bad')\n"
            "```\n"
            "FILE: src/main.py\n"
            "```python\n"
            "x = 1\n"
            "```\n"
        )
        result = parse_code_files(text)
        assert result.files == {"src/main.py": "x = 1"}
        assert any("absolute path" in w for w in result.warnings)
        assert any("traversal" in w for w in result.warnings)


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
