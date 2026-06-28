# Self-Healing Execution Agent — Design

**Date:** 2026-06-25  
**Option:** A (deep self-healing Execution Agent)  
**Status:** Approved for implementation

## 1. Problem

The current Execution Agent is a single-shot code generator. It writes files and hopes they work. It does not:

- validate file paths or LLM output format,
- install dependencies,
- run tests, type-checks, or lints,
- repair its own failures,
- return a real status other than `completed`,
- generate operational files (`.gitignore`, CI, lockfiles, etc.).

As a result, downstream agents (Test, QA) frequently reject trivial structural defects, and the pipeline cannot reliably produce a production-grade codebase.

## 2. Goal

Turn the Execution Agent into a **self-healing build agent** that:

1. robustly parses LLM-generated files,
2. validates that files are safe and structurally complete,
3. installs dependencies and runs tests/type-checks/lints,
4. fixes its own failures with an inner LLM loop,
5. generates production hygiene files,
6. reports real status (`completed` / `failed` / `needs-rework`) to the orchestrator.

## 3. Non-Goals

- Milestone-by-milestone execution (Option B) — out of scope for this iteration.
- Multi-file in-place editing/diffing — kept simple; failures trigger a focused regeneration of the whole workspace.
- Support for every language/stack — first-class Python and Node.js; generic fallback for others.
- Human-in-the-loop approval checkpoint — frontend already describes it, but not implemented yet.

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ExecutionAgent.run()                     │
│  1. Prepare workspace                                        │
│  2. Generate files via LLM                                   │
│  3. Parse & sanitize files  ──► ParserResult                │
│  4. Write files + hygiene files                              │
│  5. Build/test/fix loop (up to MAX_EXECUTION_FIX_ITERATIONS) │
│       BuildRunner.validate() ──► BuildResult                │
│       if failures: ask LLM for fix, regenerate files         │
│  6. Write implementation summary                             │
│  7. Return AgentResult(status)                               │
└─────────────────────────────────────────────────────────────┘
```

New modules:

- `src/execution_parser.py` — robust `FILE:`/fenced-block parser with path validation.
- `src/execution_build.py` — project detection, dependency install, test/type-check/lint runner.
- `src/execution_hygiene.py` — templates for `.gitignore`, GitHub Actions CI, `.env.example`, pre-commit.

Refactored modules:

- `src/agents/execution.py` — integrate parser, hygiene, build runner, and fix loop.
- `src/orchestrator.py` — handle `failed`/`needs-rework` statuses from Execution Agent.
- `agents/execution/AGENT.md` — update responsibilities and success criteria.

## 5. File Parser (`src/execution_parser.py`)

Requirements:

- Support `FILE:` markers and triple-backtick or tilde fences.
- Allow optional language tag after opening fence.
- Handle nested backticks by matching the exact opening fence length.
- Skip explanatory text between files.
- Sanitize paths: reject absolute paths, parent-directory traversal (`../`), and paths outside the workspace.
- Reject dangerous paths (e.g., `.env` with secrets is OK to write, but `/etc/passwd` is not).
- Return `ParserResult(files: dict[str,str], warnings: list[str], error: str | None)`.

## 6. Build Runner (`src/execution_build.py`)

### 6.1 Project type detection

Detect Python vs Node.js from workspace root files:
- `package.json` → `node`
- `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg` → `python`
- otherwise `unknown`

### 6.2 Dependency install

- Python: `pip install -r requirements.txt` if present; else `pip install -e .` if `pyproject.toml`/`setup.py`.
- Node: `npm install`.
- Capture stdout/stderr and exit code; time out after 5 minutes.

### 6.3 Tests

- Python: `python -m pytest tests/ test/ -q` (whichever exists).
- Node: read `package.json` `scripts.test` and run via `npm test` or the detected runner (vitest/jest).

### 6.4 Type checks

- Python: run `mypy` if `pyproject.toml` contains `[tool.mypy]` or `mypy.ini` exists.
- Node: run `tsc --noEmit` if `tsconfig.json` exists.

### 6.5 Lint

- Python: run `ruff check .` if `pyproject.toml` contains `[tool.ruff]` or `ruff.toml` exists.
- Node: run `eslint` if `.eslintrc.*` or `eslint.config.*` exists.

### 6.6 BuildResult

```python
@dataclass
class BuildResult:
    success: bool
    project_type: str
    install_output: str
    install_ok: bool
    test_output: str
    tests_ok: bool
    typecheck_output: str
    typecheck_ok: bool | None  # None if skipped
    lint_output: str
    lint_ok: bool | None       # None if skipped
    diagnostics: list[str]     # Human-readable failure summary
```

## 7. Hygiene Files (`src/execution_hygiene.py`)

For every generated project, also write:

- `.gitignore` — stack-specific (Python/Node/generic).
- `.github/workflows/ci.yml` — install + test + lint + type-check.
- `.env.example` — document expected environment variables inferred from architecture text.
- `.pre-commit-config.yaml` — optional, only if tooling config exists.

These are **templates**, not generated by LLM, to guarantee correctness and avoid extra tokens.

## 8. Execution Agent Flow

```python
async def run(context):
    workspace = prepare_workspace(run_id)
    files, warnings = generate_and_parse(context)  # LLM + parser
    write_files(files)
    write_hygiene_files(project_type, architecture)

    for i in range(MAX_EXECUTION_FIX_ITERATIONS):
        build = BuildRunner.validate(workspace)
        if build.success:
            break
        if i == MAX_EXECUTION_FIX_ITERATIONS - 1:
            return failed_result(build)
        fix_prompt = build_fix_prompt(context, files, build)
        files, warnings = generate_and_parse_with_prompt(fix_prompt)
        write_files(files)
    else:
        # no break → failed
        return failed_result(build)

    summary = build_summary(files, build)
    artifact_manager.write("execution", summary)
    return completed_result(summary, build)
```

`MAX_EXECUTION_FIX_ITERATIONS` defaults to 3 and is added to `Config`.

## 9. Orchestrator Changes

Currently the orchestrator runs `execution → test → qa` unconditionally. With the Execution Agent now self-testing, update the flow:

- If Execution returns `failed`: finish run as `failed` at the execution stage.
- If Execution returns `needs-rework`: loop back to Execution (same as QA reject, but surfaced from inside the agent).
- Otherwise proceed to Test Agent for independent verification and QA.

This prevents wasting QA cycles on broken builds.

## 10. LLM Prompts

### 10.1 Generation prompt

- Keep the existing `FILE:`/fenced-block format.
- Add explicit instructions:
  - Include dependency manifest.
  - Include tests.
  - Do not use external services unless required.
  - Include type hints/annotations for Python.
  - Keep CLI entry points testable.

### 10.2 Fix prompt

Given previous files + `BuildResult.diagnostics`, ask the LLM to produce a corrected full file set. Emphasize minimal changes and preserving tests.

## 11. Fallback Code

The deterministic fallback (used when LLM is unavailable) must itself be buildable:

- `pyproject.toml` with `pytest` dev dependency.
- `src/__init__.py`, `src/main.py`.
- `tests/test_main.py`.
- `.gitignore`, `README.md`.

This keeps the pipeline deterministic even without API keys.

## 12. Testing Strategy

1. **Parser unit tests** — multiple files, empty files, nested fences, invalid paths, mixed fence styles.
2. **Build runner unit tests** — detect project type, run tests on synthetic Python/Node workspaces.
3. **Execution agent integration tests** — mock `call_llm` to return valid code; verify workspace passes build.
4. **Execution agent fallback test** — verify fallback project builds and tests pass.
5. **Orchestrator test update** — ensure run still completes; execution status is respected.

## 13. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Build runner installs untrusted packages from generated manifests | Runs in isolated workspace; no system-wide install. Timeout limits damage. |
| Extra LLM calls increase cost | Cap `MAX_EXECUTION_FIX_ITERATIONS` at 3; skip fix loop if no tests exist. |
| Tests fail for legitimate external-dependency reasons | Agent instructions prefer self-contained MVPs; BuildResult distinguishes install vs test failures. |
| Generated Node projects need npm which may not be installed | Build runner reports `install_ok=False`; agent can fall back or return `failed`. |
| Breaking existing orchestrator test | Update fallback code to be buildable; mock build runner where needed. |

## 14. Migration

1. Implement new modules.
2. Refactor `src/agents/execution.py`.
3. Update orchestrator status handling.
4. Add/update tests.
5. Run full test suite.
6. Update `agents/execution/AGENT.md` and root `AGENTS.md` if conventions change.
