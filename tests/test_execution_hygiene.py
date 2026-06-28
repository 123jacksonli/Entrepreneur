"""Tests for execution hygiene file generation."""

from src.execution_hygiene import build_hygiene_files


class TestHygieneFiles:
    def test_python_hygiene_includes_gitignore_and_ci(self):
        hygiene = build_hygiene_files("python")
        files = hygiene.to_dict()
        assert ".gitignore" in files
        assert ".github/workflows/ci.yml" in files
        assert ".env.example" in files
        assert ".pre-commit-config.yaml" in files
        assert "__pycache__" in files[".gitignore"]
        assert "pytest" in files[".github/workflows/ci.yml"]

    def test_node_hygiene_includes_npm_ignore(self):
        hygiene = build_hygiene_files("node")
        files = hygiene.to_dict()
        assert ".gitignore" in files
        assert "node_modules" in files[".gitignore"]
        assert "npm ci" in files[".github/workflows/ci.yml"]

    def test_generic_hygiene_is_minimal(self):
        hygiene = build_hygiene_files("unknown")
        files = hygiene.to_dict()
        assert ".gitignore" in files
        assert ".env.example" in files
        assert ".github/workflows/ci.yml" not in files
        assert ".pre-commit-config.yaml" not in files
