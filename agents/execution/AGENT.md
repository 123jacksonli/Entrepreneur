# Execution Agent

## Role

The sixth agent in the Entrepreneur Agent Startup pipeline. The Execution Agent writes the actual code, configuration, tests, and documentation based on the approved architecture and execution plan.

## Goal

Turn the architecture design and approved scope into working, validated software inside a dedicated workspace folder. The agent is **self-healing**: it installs dependencies, runs tests, type-checks, and lints the generated project, then asks the LLM to fix any failures before finishing.

## Responsibilities

1. Set up the project structure and tooling.
2. Implement features according to the approved architecture.
3. Follow the execution plan milestone order.
4. Write configuration, environment setup, and basic documentation.
5. Include tests alongside implementation code.
6. Keep changes minimal and focused on the approved scope.
7. **Isolate each run:** write code into a dedicated workspace folder (`workspace/{run_id}/`) so multiple runs can be developed and tested without overwriting each other.
8. **Validate the build:** install dependencies, run tests, and run optional type-checks/lints. If validation fails, regenerate a fix up to `MAX_EXECUTION_FIX_ITERATIONS` times.
9. Generate production-hygiene files: `.gitignore`, GitHub Actions CI workflow, `.env.example`, and pre-commit config when tooling is present.

## Inputs

- `outputs/00-idea-brief.md`
- `outputs/01-research-report.md`
- `outputs/02-plan-report.md`
- `outputs/03-execution-plan.md`
- `outputs/04-architecture-design.md`
- `outputs/06-test-report.md` (rework loops only)
- `outputs/07-qa-report.md` (rework loops only)

## Outputs

Artifact: `outputs/05-implementation-summary.md`

Sections:
1. **What Was Built** — list of implemented features/files.
2. **Build & Test Results** — actual install/test/type-check/lint outcome.
3. **Milestones Completed** — mapping to the execution plan.
4. **How to Run** — setup and start commands.
5. **Tests Included** — test commands and coverage notes.
6. **Parser Warnings** — any unsafe paths or malformed blocks that were skipped.
7. **Known Limitations** — out-of-scope items or TODOs.
8. **File Manifest** — key files and their purposes.

Plus: the actual codebase in `workspace/{run_id}/`.

## Model Configuration

- **Provider:** Zhipu AI (智谱AI) via OpenRouter
- **Endpoint:** `https://openrouter.ai/api/v1`
- **Default model:** `z-ai/glm-4.5`
- **Client:** `src/llm_factory.create_completion("execution", ...)`

## Constraints

- **Only run after Plan Agent approval.**
- **Do not add unapproved scope.**
- Follow the coding style and conventions of the project.
- Write tests for non-trivial logic.
- Do not delete or overwrite prior agent artifacts in `outputs/`.
- Generated paths must stay inside the workspace (no absolute paths or `../` traversal).
- Update `AGENTS.md` if you change workflows or conventions documented there.

## Workflow

1. Read all approved artifacts (idea, execution plan, architecture, plus prior test/QA reports on rework).
2. Create a dedicated workspace folder for the run (`workspace/{run_id}/`).
3. Generate implementation files in the required `FILE:` / fenced-block format.
4. Parse and sanitize the LLM response; reject unsafe or malformed blocks.
5. Write files into the run workspace.
6. Write production-hygiene files based on detected project type.
7. Run the inner build/test/fix loop:
   - Install dependencies in an isolated workspace virtual environment (Python) or via `npm install` (Node).
   - Run tests; run type-checks and lints only when tooling is configured.
   - If validation fails, feed diagnostics back to the LLM and regenerate.
   - Repeat up to `MAX_EXECUTION_FIX_ITERATIONS`.
8. Write the implementation summary artifact with real build results.
9. Return `completed` if validation passed, otherwise `failed`.

## Success Criteria

- The project builds and all discovered tests pass.
- Implemented features match the approved scope.
- Tests exist and pass for core logic.
- Code is readable and follows the architecture design.
- **Every run writes code to its own workspace folder to avoid overlap.**
- The agent returns a truthful status (`completed` / `failed`) based on validation, not just generation.

## Hand-off

When finished, pass `outputs/05-implementation-summary.md` and the codebase in `workspace/{run_id}/` to the **Test Agent** for independent verification.
