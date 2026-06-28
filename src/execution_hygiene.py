"""Production-hygiene file templates for generated workspaces.

The Execution Agent writes these files alongside generated code so that every
workspace is immediately ready for version control, CI, and local development.
"""

from __future__ import annotations

from dataclasses import dataclass


_PYTHON_GITIGNORE = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
.venv/
venv/
ENV/
env/

# Test / coverage
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
.mypy_cache/
.dmypy.json
.ruff_cache/

# Editors
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Secrets
.env
.env.local
"""

_NODE_GITIGNORE = """# Dependencies
node_modules/
.pnp
.pnp.js

# Build outputs
dist/
build/
coverage/
*.tsbuildinfo

# Test / cache
.nyc_output/
.cache/

# Environment
.env
.env.local
.env.*.local

# Editors
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
"""

_GENERIC_GITIGNORE = """# Build artifacts
build/
dist/
coverage/

# Dependencies
node_modules/
.venv/
venv/

# Test / cache
.pytest_cache/
.cache/

# Environment and secrets
.env
.env.local

# Editors
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
"""

_GITHUB_ACTIONS_PYTHON = """name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m venv .venv
          source .venv/bin/activate
          pip install --upgrade pip
          pip install -e ".[dev]" || pip install -e .
          pip install pytest
      - name: Run tests
        run: |
          source .venv/bin/activate
          pytest tests/ -q
      - name: Run type check
        if: hashFiles('mypy.ini', 'pyproject.toml') != ''
        run: |
          source .venv/bin/activate
          pip install mypy
          mypy src/
      - name: Run lint
        if: hashFiles('ruff.toml', '.ruff.toml', 'pyproject.toml') != ''
        run: |
          source .venv/bin/activate
          pip install ruff
          ruff check .
"""

_GITHUB_ACTIONS_NODE = """name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test
      - name: Run type check
        if: hashFiles('tsconfig.json') != ''
        run: npx tsc --noEmit
      - name: Run lint
        if: hashFiles('.eslintrc.*', 'eslint.config.*') != ''
        run: npx eslint .
"""

_ENV_EXAMPLE = """# Copy this file to .env and fill in real values.
# Example environment variables inferred from the architecture design.

# Add your configuration keys below:
# API_KEY=your_api_key_here
# DATABASE_URL=sqlite:///app.db
"""

_PRE_COMMIT_PYTHON = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
"""

_PRE_COMMIT_NODE = """repos:
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.0.0
    hooks:
      - id: eslint
"""


@dataclass
class HygieneFiles:
    """Collection of production-hygiene files to write into a workspace."""

    gitignore: str = ""
    ci_workflow: str = ""
    env_example: str = ""
    pre_commit_config: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Return a relative-path -> content mapping of all non-empty files."""
        files: dict[str, str] = {}
        if self.gitignore:
            files[".gitignore"] = self.gitignore
        if self.ci_workflow:
            files[".github/workflows/ci.yml"] = self.ci_workflow
        if self.env_example:
            files[".env.example"] = self.env_example
        if self.pre_commit_config:
            files[".pre-commit-config.yaml"] = self.pre_commit_config
        return files


def build_hygiene_files(project_type: str) -> HygieneFiles:
    """Return hygiene file contents appropriate for the detected project type."""
    if project_type == "python":
        return HygieneFiles(
            gitignore=_PYTHON_GITIGNORE,
            ci_workflow=_GITHUB_ACTIONS_PYTHON,
            env_example=_ENV_EXAMPLE,
            pre_commit_config=_PRE_COMMIT_PYTHON,
        )
    if project_type == "node":
        return HygieneFiles(
            gitignore=_NODE_GITIGNORE,
            ci_workflow=_GITHUB_ACTIONS_NODE,
            env_example=_ENV_EXAMPLE,
            pre_commit_config=_PRE_COMMIT_NODE,
        )
    return HygieneFiles(
        gitignore=_GENERIC_GITIGNORE,
        ci_workflow="",
        env_example=_ENV_EXAMPLE,
        pre_commit_config=None,
    )
