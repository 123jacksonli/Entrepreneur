"""Tests for the execution build runner."""

from pathlib import Path

import pytest

from src.config import Config
from src.execution_build import BuildRunner


class TestBuildRunner:
    @pytest.fixture
    def python_workspace(self, tmp_path, monkeypatch):
        """Create a minimal buildable Python workspace."""
        monkeypatch.setattr(Config, "WORKSPACE_DIR", str(tmp_path / "workspace"))
        workspace = tmp_path / "workspace" / "run-1"
        workspace.mkdir(parents=True)

        (workspace / "pyproject.toml").write_text(
            """[project]
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
"""
        )
        (workspace / "src" / "demo").mkdir(parents=True)
        (workspace / "src" / "demo" / "__init__.py").write_text("")
        (workspace / "src" / "demo" / "main.py").write_text(
            "def add(a, b):\n    return a + b\n"
        )
        (workspace / "tests").mkdir()
        (workspace / "tests" / "test_main.py").write_text(
            "from demo.main import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
        )
        return workspace

    def test_detect_python_project(self, python_workspace):
        runner = BuildRunner(python_workspace)
        assert runner.detect_project_type() == "python"

    def test_detect_node_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "WORKSPACE_DIR", str(tmp_path / "workspace"))
        workspace = tmp_path / "workspace" / "run-node"
        workspace.mkdir(parents=True)
        (workspace / "package.json").write_text('{"name": "demo"}')

        runner = BuildRunner(workspace)
        assert runner.detect_project_type() == "node"

    def test_detect_unknown_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "WORKSPACE_DIR", str(tmp_path / "workspace"))
        workspace = tmp_path / "workspace" / "run-empty"
        workspace.mkdir(parents=True)

        runner = BuildRunner(workspace)
        assert runner.detect_project_type() == "unknown"
        result = runner.validate()
        assert result.success is False
        assert "Could not detect project type" in result.diagnostics[0]

    def test_validate_passes_for_valid_python_project(self, python_workspace):
        runner = BuildRunner(python_workspace)
        result = runner.validate()
        assert result.success is True
        assert result.project_type == "python"
        assert result.install_ok is True
        assert result.tests_ok is True

    def test_validate_fails_when_test_breaks(self, python_workspace):
        # Break the test.
        (python_workspace / "tests" / "test_main.py").write_text(
            "from demo.main import add\n\ndef test_add():\n    assert add(2, 3) == 99\n"
        )
        runner = BuildRunner(python_workspace)
        result = runner.validate()
        assert result.success is False
        assert result.tests_ok is False
        assert "Tests failed" in result.diagnostics[0]

    def test_validate_skips_typecheck_without_config(self, python_workspace):
        runner = BuildRunner(python_workspace)
        result = runner.validate()
        assert result.typecheck_ok is None

    def test_validate_runs_typecheck_when_configured(self, python_workspace):
        pyproject = python_workspace / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")
        pyproject.write_text(text + "\n[tool.mypy]\npython_version = \"3.11\"\n")

        runner = BuildRunner(python_workspace)
        result = runner.validate()
        # mypy may or may not be installed; we just verify it is attempted.
        assert result.typecheck_ok is not None or "mypy" in result.typecheck_output.lower()
