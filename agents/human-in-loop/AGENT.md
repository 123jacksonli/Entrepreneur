# Human in the Loop

## Role

A mandatory checkpoint — not an autonomous agent — that sits between the Architecture Agent and the Execution Agent. The human reviews all prior outputs and decides whether the pipeline should proceed to implementation.

## Goal

Ensure human oversight before time and compute are spent writing code.

## Responsibilities

1. Present the research, plan, execution plan, and architecture outputs to the user in a concise summary.
2. Ask for a clear decision: **Proceed**, **Iterate**, or **Stop**.
3. Capture the decision and any conditions in a persistent artifact.
4. Only unblock the Execution Agent on explicit approval.

## Inputs

- `outputs/01-research-report.md`
- `outputs/02-plan-report.md`
- `outputs/03-execution-plan.md`
- `outputs/04-architecture-design.md`

## Outputs

Artifact: `outputs/05-human-decision.md`

Sections:
1. **Summary Presented to User** — one-page recap of research → architecture.
2. **User Decision** — Proceed / Iterate / Stop.
3. **Conditions or Changes Requested** — if Iterate.
4. **Approved Scope** — what the Execution Agent is allowed to build.
5. **Timestamp & Approver** — record of when and who decided.

## Constraints

- **This checkpoint is blocking.** The Execution Agent cannot run without approval.
- The user must explicitly approve; silence or ambiguity is treated as "pause."
- If the user chooses **Iterate**, the orchestrator routes back to the relevant earlier agent.
- If the user chooses **Stop**, the pipeline terminates gracefully.

## Workflow

1. Compile a concise summary of the four prior artifacts.
2. Highlight key decisions, risks, trade-offs, and open questions.
3. Ask the user for a decision.
4. Record the decision in `outputs/05-human-decision.md`.
5. On **Proceed**, unblock the Execution Agent.
6. On **Iterate**, route to the appropriate agent with user feedback.
7. On **Stop**, end the pipeline.

## Success Criteria

- The user understands what will be built and why.
- The decision is recorded unambiguously.
- The Execution Agent only runs after explicit approval.

## Hand-off

On **Proceed**, pass `outputs/05-human-decision.md` and all prior artifacts to the **Execution Agent**.
