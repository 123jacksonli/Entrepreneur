# Downloaded Superpowers Skills

These skills are downloaded from <https://github.com/abudhahir/superpowers/tree/main/skills>.

## Included Skills

| Skill | Files | Purpose |
|-------|-------|---------|
| `brainstorming` | SKILL.md | Clarify requirements before building |
| `dispatching-parallel-agents` | SKILL.md | Run independent agents in parallel |
| `executing-plans` | SKILL.md | Execute implementation plans step by step |
| `finishing-a-development-branch` | SKILL.md | Wrap up and merge branches cleanly |
| `receiving-code-review` | SKILL.md | Process review feedback constructively |
| `requesting-code-review` | SKILL.md, code-reviewer.md | Request and run code reviews |
| `subagent-driven-development` | SKILL.md + prompts | Delegate implementation to subagents |
| `systematic-debugging` | SKILL.md + references/tools | Debug methodically |
| `test-driven-development` | SKILL.md + anti-patterns | TDD discipline |
| `using-git-worktrees` | SKILL.md | Use git worktrees |
| `using-superpowers` | SKILL.md | Meta-skill on finding/using skills |
| `verification-before-completion` | SKILL.md | Verify before declaring done |
| `writing-plans` | SKILL.md | Write implementation plans |
| `writing-skills` | SKILL.md + references/tools | Create and test skills |

## Important Note: Kimi Code CLI Compatibility

These skills were originally written for **Claude Code / Codex**. Some references may need adaptation for Kimi Code CLI:

- `Skill` tool → Kimi Code CLI loads skills automatically from `.kimi/skills/`.
- `TodoWrite` tool → Use `SetTodoList` instead.
- `CLAUDE.md` → Use `AGENTS.md` instead.
- `~/.claude/skills` → Use `.kimi/skills/` for project-level skills.

If you want these adapted to Kimi Code CLI conventions, ask the agent to perform the replacements.
