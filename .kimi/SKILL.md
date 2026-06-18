---
name: entrepreneur-project-skill
description: Project skill for the Entrepreneur Agent Startup. Use for every task in this repository. Enforces Superpowers workflow (brainstorming, planning, TDD, systematic debugging, verification), git commit discipline, and coordination with AGENTS.md agent pipeline.
---

# Project Skill: Entrepreneur Agent Startup

This skill combines the Entrepreneur Agent Startup pipeline with the Superpowers agentic development methodology (adapted for Kimi Code CLI).

Source: https://github.com/obra/superpowers

## Rule 1: Respect the Agent Pipeline

This project is an **agent-driven startup builder**. Before writing implementation code, the pipeline defined in `AGENTS.md` should be followed:

1. **Research Agent** — gather market data and trends.
2. **Plan Agent** — competitor analysis and feasibility check.
3. **Execution Plan Agent** — milestones, tasks, timeline.
4. **Architecture Agent** — tech stack, components, APIs, data models.
5. **Human in the Loop** — mandatory approval gate.
6. **Execution Agent** — write code.
7. **Test Agent** — run tests and report bugs.
8. **QA Agent** — challenge output and accept/reject.

For routine implementation tasks within an already-approved scope, you may act as the Execution Agent directly. For new features, significant changes, or ambiguous requirements, run the relevant agent stage first.

## Rule 2: Commit After Every Completed Task

Whenever you finish a task (feature, bug fix, refactor, test addition, or agent artifact), **immediately create a git commit** and tell the user what you did in the commit message.

1. **Commit after every completed task** — do not batch multiple unrelated changes into a single commit.
2. **Use descriptive commit messages** that explain:
   - What was added, changed, or fixed
   - Why (if the reason is not obvious)
   - Any breaking changes or migration notes
3. **Ask for confirmation** before committing if the task involves:
   - Deleting files
   - Modifying existing user configuration
   - Changes that could affect production data
4. **Never run `git push`** unless explicitly asked.

## Rule 3: Follow the Superpowers Workflow

For any non-trivial task (new feature, bug fix, refactor, architecture change), follow this workflow:

### 3.1 Brainstorm Before Building

Before writing code, clarify what we are building:

- Ask clarifying questions if requirements are ambiguous.
- Explore alternatives and trade-offs briefly.
- Confirm the scope and success criteria with the user.
- For small, obvious fixes or one-liners, this can be skipped.

### 3.2 Write a Plan for Non-Trivial Work

If the task spans multiple files or steps, write an implementation plan first.

- Save the plan to `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`.
- Break work into bite-sized tasks (2–5 minutes each).
- Include exact file paths for creates/modifies/tests.
- Include exact commands to run and expected outcomes.
- Emphasize TDD, DRY, and YAGNI.
- Use `SetTodoList` to track the plan items.

### 3.3 Test-Driven Development (TDD)

For new features and bug fixes:

1. **RED**: Write a failing test first.
2. **Verify RED**: Run the test and confirm it fails for the expected reason.
3. **GREEN**: Write the minimal code to make the test pass.
4. **Verify GREEN**: Run the test and confirm it passes.
5. **REFACTOR**: Clean up duplication and names while keeping tests green.

**No production code without a failing test first.** If you already wrote code before the test, delete it and start over with TDD.

Exceptions (ask user first): throwaway prototypes, pure configuration files, generated code.

### 3.4 Systematic Debugging

When encountering bugs or test failures:

1. **Root Cause Investigation**: read errors carefully, reproduce consistently, check recent changes, trace data flow.
2. **Pattern Analysis**: find working examples, compare differences.
3. **Hypothesis and Testing**: form one hypothesis, test minimally.
4. **Implementation**: create a failing test reproducing the bug, fix the root cause, verify.

If 3+ fix attempts fail, stop and question the architecture before trying more.

### 3.5 Verification Before Completion

Before declaring a task complete:

- Run the relevant tests and confirm they pass.
- Check that no other tests broke.
- Verify the actual behavior matches the requirement.
- Review your own code for obvious issues.
- Create a git commit per Rule 2.

### 3.6 Use Subagents for Complex Work

For complex multi-step tasks, use the `Agent` tool to dispatch focused subagents:

- Give each subagent a clear, self-contained task.
- Review subagent output before accepting it.
- Prefer fresh subagents for independent investigation tasks.

## Rule 4: Keep It Simple

- Prefer minimal, focused changes.
- Follow existing project patterns and conventions.
- Avoid over-engineering. YAGNI.
- Update `AGENTS.md` when modifying workflows or architecture it describes.
