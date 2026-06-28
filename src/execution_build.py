"""Build, test, and validation runner for generated workspaces.

The Execution Agent uses BuildRunner to verify that the code it produced is
runnable: dependencies install, tests pass, and optional type-checks/lints
succeed. The runner is intentionally conservative and stack-agnostic at the
edges; first-class support is provided for Python and Node.js projects.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    success: bool
    project_type: str
    install_output: str = ""
    install_ok: bool = False
    test_output: str = ""
    tests_ok: bool = False
    typecheck_output: str = ""
    typecheck_ok: bool | None = None
    lint_output: str = ""
    lint_ok: bool | None = None
    diagnostics: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return a concise human-readable summary of the build."""
        lines = [
            f"Project type: {self.project_type}",
            f"Dependencies installed: {'yes' if self.install_ok else 'no'}",
            f"Tests: {'passed' if self.tests_ok else 'failed'}",
        ]
        if self.typecheck_ok is not None:
            lines.append(f"Type check: {'passed' if self.typecheck_ok else 'failed'}")
        if self.lint_ok is not None:
            lines.append(f"Lint: {'passed' if self.lint_ok else 'failed'}")
        if self.diagnostics:
            lines.append("Diagnostics:")
            lines.extend(f"  - {d}" for d in self.diagnostics)
        return "\n".join(lines)


class BuildRunner:
    """Run validation steps against a generated project workspace."""

    # Subprocess timeout for individual commands (seconds).
    TIMEOUT: ClassVar[int] = 300

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace).resolve()

    def validate(self) -> BuildResult:
        """Run the full validation pipeline and return a BuildResult."""
        project_type = self.detect_project_type()
        if project_type == "unknown":
            return BuildResult(
                success=False,
                project_type="unknown",
                diagnostics=[
                    "Could not detect project type. "
                    "No package.json, pyproject.toml, requirements.txt, setup.py, or setup.cfg found."
                ],
            )

        install_output = self._install_dependencies(project_type)
        install_ok = self._command_succeeded(install_output)

        test_output, tests_ok = self._run_tests(project_type)

        typecheck_output, typecheck_ok = self._run_typecheck(project_type)
        lint_output, lint_ok = self._run_lint(project_type)

        diagnostics: list[str] = []
        if not install_ok:
            diagnostics.append("Dependency installation failed.")
        if not tests_ok:
            diagnostics.append("Tests failed or were not discovered.")
        if typecheck_ok is False:
            diagnostics.append("Type check failed.")
        if lint_ok is False:
            diagnostics.append("Lint failed.")

        success = install_ok and tests_ok and typecheck_ok is not False and lint_ok is not False

        return BuildResult(
            success=success,
            project_type=project_type,
            install_output=install_output,
            install_ok=install_ok,
            test_output=test_output,
            tests_ok=tests_ok,
            typecheck_output=typecheck_output,
            typecheck_ok=typecheck_ok,
            lint_output=lint_output,
            lint_ok=lint_ok,
            diagnostics=diagnostics,
        )

    def detect_project_type(self) -> str:
        """Detect whether the workspace is a Python or Node.js project."""
        if (self.workspace / "package.json").exists():
            return "node"
        if any(
            (self.workspace / name).exists()
            for name in ("requirements.txt", "pyproject.toml", "setup.py", "setup.cfg")
        ):
            return "python"
        return "unknown"

    def _detect_dev_extras(self) -> str:
        """Return the name of the dev extra if the project declares one.

        Looks for ``[project.optional-dependencies]`` in pyproject.toml or
        ``extras_require`` in setup.py. Returns an empty string if none found.
        """
        pyproject = self.workspace / "pyproject.toml"
        if pyproject.exists():
            text = pyproject.read_text(encoding="utf-8")
            # Very small heuristic parser: find a ``dev = [`` line under an
            # optional-dependencies section.
            in_optional = False
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("[project.optional-dependencies]"):
                    in_optional = True
                    continue
                if in_optional:
                    if stripped.startswith("["):
                        in_optional = False
                    elif stripped.startswith("dev") and "=" in stripped:
                        return "dev"

        setup_py = self.workspace / "setup.py"
        if setup_py.exists():
            text = setup_py.read_text(encoding="utf-8")
            if "extras_require" in text and '"dev"' in text:
                return "dev"

        return ""

    def _ensure_python_venv(self) -> Path | None:
        """Create a Python virtual environment inside the workspace if absent."""
        venv_dir = self.workspace / ".venv"
        python = self._venv_executable("python")
        if python.exists():
            return python

        if shutil.which("python3") is None:
            return None

        result = self._run_subprocess(
            ["python3", "-m", "venv", str(venv_dir)],
        )
        if result.returncode != 0:
            return None

        # Upgrade pip to avoid externally-managed-environment issues.
        pip = self._venv_executable("pip")
        self._run_subprocess([str(pip), "install", "--upgrade", "pip"])

        return self._venv_executable("python")

    def _venv_executable(self, name: str) -> Path:
        """Return the path to an executable inside the workspace venv."""
        import sys

        if sys.platform.startswith("win"):
            return self.workspace / ".venv" / "Scripts" / f"{name}.exe"
        return self.workspace / ".venv" / "bin" / name

    def _install_dependencies(self, project_type: str) -> str:
        """Install dependencies and return captured output."""
        if project_type == "node":
            if shutil.which("npm") is None:
                return "npm not available; cannot install Node.js dependencies."
            return self._run_command(["npm", "install"])

        if project_type == "python":
            venv_python = self._ensure_python_venv()
            if venv_python is None:
                return "Could not create a Python virtual environment."
            pip = self._venv_executable("pip")
            outputs: list[str] = []

            req_file = self.workspace / "requirements.txt"
            if req_file.exists():
                outputs.append(
                    self._run_command([str(pip), "install", "-r", str(req_file)])
                )

            has_setup = any(
                (self.workspace / name).exists()
                for name in ("pyproject.toml", "setup.py", "setup.cfg")
            )
            if has_setup:
                # Prefer installing with the dev extra if one is declared.
                extras = self._detect_dev_extras()
                if extras:
                    outputs.append(
                        self._run_command([str(pip), "install", "-e", f".[{extras}]"])
                    )
                else:
                    outputs.append(
                        self._run_command([str(pip), "install", "-e", "."])
                    )

            if not req_file.exists() and not has_setup:
                return "No Python dependency manifest found; skipping install."

            # Ensure pytest is available in the workspace venv so tests can run
            # even if the generated project forgot to declare it.
            outputs.append(
                self._run_command([str(pip), "install", "--upgrade", "pytest"])
            )
            return "\n".join(outputs)

        return "No dependency manifest found; skipping install."

    def _run_tests(self, project_type: str) -> tuple[str, bool]:
        """Run tests and return (output, passed)."""
        if project_type == "node":
            result = self._run_node_tests()
        elif project_type == "python":
            result = self._run_python_tests()
        else:
            return "Unknown project type; cannot run tests.", False

        output = result.stdout + "\n" + result.stderr
        return output.strip(), result.returncode == 0

    def _run_python_tests(self) -> subprocess.CompletedProcess[str]:
        """Run pytest in a Python workspace using the workspace virtual env."""
        test_dirs = [self.workspace / "tests", self.workspace / "test"]
        test_dir = next((d for d in test_dirs if d.exists() and d.is_dir()), None)

        if test_dir is None:
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="No tests/ or test/ directory found in the generated project.",
            )

        python = self._venv_executable("python")
        return self._run_subprocess(
            [str(python), "-m", "pytest", str(test_dir), "-q"],
        )

    def _run_node_tests(self) -> subprocess.CompletedProcess[str]:
        """Run tests in a Node.js workspace."""
        package_json = self.workspace / "package.json"
        if not package_json.exists():
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="No package.json found.",
            )

        try:
            scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {})
        except json.JSONDecodeError as exc:
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr=f"Could not parse package.json: {exc}",
            )

        test_script = scripts.get("test", "")
        node_modules = self.workspace / "node_modules"

        def runner_exists(name: str) -> bool:
            return (node_modules / ".bin" / name).exists() or shutil.which(name) is not None

        test_script_lower = test_script.lower()
        if "vitest" in test_script_lower or runner_exists("vitest"):
            cmd = ["npx", "vitest", "run", "--reporter=verbose"]
        elif "jest" in test_script_lower or runner_exists("jest"):
            cmd = ["npx", "jest", "--runInBand"]
        elif test_script:
            # Generic test script; run it once. Avoid watch-mode scripts.
            cmd = ["npm", "test", "--", "--run"]
        else:
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="No 'test' script in package.json and no test runner found.",
            )

        return self._run_subprocess(cmd)

    def _run_typecheck(self, project_type: str) -> tuple[str, bool | None]:
        """Run a type check if tooling is configured. Returns None if skipped."""
        if project_type == "python":
            if not self._has_mypy_config():
                return "No mypy configuration found; skipping type check.", None
            python = self._venv_executable("python")
            output = self._run_command([str(python), "-m", "mypy", str(self.workspace)])
            return output, self._command_succeeded(output)

        if project_type == "node":
            if not (self.workspace / "tsconfig.json").exists():
                return "No tsconfig.json found; skipping type check.", None
            if shutil.which("npx") is None:
                return "npx not available; skipping type check.", None
            output = self._run_command(["npx", "tsc", "--noEmit"])
            return output, self._command_succeeded(output)

        return "Unknown project type; skipping type check.", None

    def _run_lint(self, project_type: str) -> tuple[str, bool | None]:
        """Run a linter if tooling is configured. Returns None if skipped."""
        if project_type == "python":
            if not self._has_ruff_config():
                return "No ruff configuration found; skipping lint.", None
            python = self._venv_executable("python")
            output = self._run_command([str(python), "-m", "ruff", "check", "."])
            return output, self._command_succeeded(output)

        if project_type == "node":
            if not self._has_eslint_config():
                return "No ESLint configuration found; skipping lint.", None
            if shutil.which("npx") is None:
                return "npx not available; skipping lint.", None
            output = self._run_command(["npx", "eslint", "."])
            return output, self._command_succeeded(output)

        return "Unknown project type; skipping lint.", None

    def _has_mypy_config(self) -> bool:
        """Return True if mypy is configured for this workspace."""
        if (self.workspace / "mypy.ini").exists():
            return True
        pyproject = self.workspace / "pyproject.toml"
        if pyproject.exists():
            text = pyproject.read_text(encoding="utf-8")
            if "[tool.mypy]" in text:
                return True
        return False

    def _has_ruff_config(self) -> bool:
        """Return True if ruff is configured for this workspace."""
        for name in ("ruff.toml", ".ruff.toml", "pyproject.toml"):
            path = self.workspace / name
            if path.exists():
                if name == "pyproject.toml":
                    text = path.read_text(encoding="utf-8")
                    if "[tool.ruff" in text:
                        return True
                else:
                    return True
        return False

    def _has_eslint_config(self) -> bool:
        """Return True if ESLint is configured for this workspace."""
        names = (
            ".eslintrc.js",
            ".eslintrc.cjs",
            ".eslintrc.yaml",
            ".eslintrc.yml",
            ".eslintrc.json",
            ".eslintrc",
            "eslint.config.js",
            "eslint.config.mjs",
            "eslint.config.cjs",
            "eslint.config.ts",
        )
        return any((self.workspace / name).exists() for name in names)

    def _command_succeeded(self, output: str) -> bool:
        """Heuristic: command output indicates failure if timeout or error words appear."""
        failure_markers = (
            "timed out",
            "timeout expired",
            "not available",
            "not installed",
            "Error installing",
        )
        lower = output.lower()
        return not any(marker in lower for marker in failure_markers)

    def _run_command(self, cmd: list[str]) -> str:
        """Run a command and return stdout+stderr as a string."""
        result = self._run_subprocess(cmd)
        output = result.stdout + "\n" + result.stderr
        return output.strip()

    def _run_subprocess(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        """Run a subprocess with timeout and return the CompletedProcess."""
        try:
            return subprocess.run(
                cmd,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT,
            )
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout=exc.stdout or "",
                stderr=f"Command timed out after {self.TIMEOUT}s.",
            )
        except Exception as exc:  # noqa: BLE001
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr=f"Error running command: {exc}",
            )
