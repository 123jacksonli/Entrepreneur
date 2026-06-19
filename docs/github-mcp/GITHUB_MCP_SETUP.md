# GitHub MCP Setup for the Execution Agent

## Why

The **Execution Agent** is required to use GitHub MCP for version control. Every milestone it completes must be committed and pushed so execution history is preserved and reversible.

## Required Tools

The Execution Agent expects these MCP server tools to be available:

- `create_repository` — create a new GitHub repo for a project.
- `create_branch` — create a feature/execution branch.
- `create_or_update_file` — commit individual files.
- `push_files` — commit multiple files in one commit.
- `create_pull_request` — optional, for review workflows.

## Authentication

GitHub MCP requires a valid **GitHub Personal Access Token (PAT)**.

### What is a PAT?

A PAT is a long string that acts like a password for programmatic GitHub access.
You create one in your GitHub account and give it specific permissions (scopes).
The Execution Agent uses it to create branches, commit files, and push code on
your behalf.

### Required scopes

Create a classic token with at least:

- `repo` — full repository access
- `workflow` — if modifying GitHub Actions

Configure the MCP server with your token. The exact method depends on your Kimi Code CLI / MCP client setup.

### Example `.mcp/config.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxx"
      }
    }
  }
}
```

> **Do not commit this token.** Keep it in environment variables or a secure vault.

## Execution Agent Workflow with GitHub MCP

1. **Before writing code**, check MCP authentication by calling `search_repositories` or `list_commits`.
2. If no repository exists, create one with `create_repository`.
3. For each milestone:
   - Implement the milestone.
   - Run tests.
   - Commit with `push_files` or `create_or_update_file`.
4. After the final milestone, write `outputs/06-implementation-summary.md` and commit it.
5. Hand off to the **Test Agent**.

## Fallback

If GitHub MCP is unavailable, the Execution Agent may use git CLI:

```bash
git add .
git commit -m "feat: <milestone description>"
git push origin <branch>
```

But MCP is preferred because it provides explicit repository/branch control without relying on local git state.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Authentication Failed: Requires authentication` | Verify `GITHUB_PERSONAL_ACCESS_TOKEN` is set and has `repo` scope. |
| `Resource not accessible by integration` | Token may lack permissions; regenerate with `repo` scope. |
| MCP tool not found | Confirm the MCP server is registered in your client config. |
