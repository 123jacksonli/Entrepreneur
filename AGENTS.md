# Entrepreneur Agent Startup — Agent Operating Manual

## 1. Project Vision

This repository builds an **agent-driven startup builder** for entrepreneurs. A user describes a business idea (or even just an interest area), and a pipeline of specialized agents autonomously refines, researches, plans, designs, builds, tests, and validates startup ideas.

> **Current phase:** agent specification. No code is written yet.

## 2. Agent Pipeline

```
┌─────────────────┐
│ Idea Generation │ ◄──────────┐
└────────┬────────┘            │
         ▼                      │ iterate
┌─────────────┐                 │
│   Research  │                 │
└──────┬──────┘                 │
       ▼                        │
┌─────────────┐    approve      │
│     Plan    │ ─────────────►  │
└──────┬──────┘                 │
       ▼                        │
┌─────────────┐
│ Exec. Plan  │  ──► Step-by-step milestones, tasks, timeline
└──────┬──────┘
       ▼
┌─────────────┐
│ Architecture│  ──► Tech stack, modules, APIs, data models
└──────┬──────┘
       ▼
┌─────────────┐
│  Execution  │  ──► Write code, config, tests, docs
└──────┬──────┘
       ▼
┌─────────────┐
│    Test     │  ──► Run tests, report bugs, coverage
└──────┬──────┘
       ▼
┌─────────────┐
│     QA      │  ──► Challenge output, accept or reject
└──────┬──────┘
       │
       └ reject ──► loop back to Execution Agent (max iterations)
```

## 3. Directory Layout

```
Entrepreneur/
├── AGENTS.md                              # this file
├── agents/
│   ├── idea-generation/AGENT.md           # Idea Generation Agent spec
│   ├── research/AGENT.md                  # Research Agent spec
│   ├── plan/AGENT.md                      # Plan Agent spec
│   ├── execution-plan/AGENT.md            # Execution Plan Agent spec
│   ├── architecture/AGENT.md              # Architecture Agent spec
│   ├── execution/AGENT.md                 # Execution Agent spec
│   ├── test/AGENT.md                      # Test Agent spec
│   └── qa/AGENT.md                        # QA Agent spec
└── .git/
```

## 4. Shared Rules

1. **One agent per step.** Each agent owns exactly one stage of the pipeline.
2. **Autonomous operation.** The pipeline runs end-to-end without human oversight. Agents make decisions, iterate, and commit code on their own.
3. **No code before Plan approval.** The Execution Agent is the only agent allowed to write implementation code, and it may only run after the Plan Agent has approved the idea.
4. **Artifacts only.** Idea Generation, Research, Plan, Execution Plan, and Architecture agents produce markdown artifacts, not runnable code.
5. **Hand-off contract.** Each agent must write its output to a clearly named artifact and signal completion to the orchestrator.
6. **Idea loop.** Idea Generation → Research → Plan form a loop. The Plan Agent approves, iterates, or stops. Only approved ideas proceed to Execution Plan. The orchestrator enforces `MAX_IDEA_ITERATIONS`.
7. **QA loop.** If QA rejects the output, the orchestrator routes rework instructions back to the Execution Agent automatically, up to `MAX_QA_ITERATIONS`.
8. **Execution Agent uses GitHub MCP.** The Execution Agent must create a dedicated branch per run, commit after each milestone to that branch, and push changes so all execution output is version-controlled. Execution never commits directly to `main`.

## 5. Artifact Naming Convention

| Stage | Output File |
|-------|-------------|
| Idea Generation | `outputs/00-idea-brief.md` |
| Research | `outputs/01-research-report.md` |
| Plan | `outputs/02-plan-report.md` |
| Execution Plan | `outputs/03-execution-plan.md` |
| Architecture | `outputs/04-architecture-design.md` |
| Execution | `outputs/05-implementation-summary.md` |
| Test | `outputs/06-test-report.md` |
| QA | `outputs/07-qa-report.md` |

## 6. Autonomous Safeguards

To prevent runaway execution and costs:

- `MAX_IDEA_ITERATIONS` — maximum times the Idea Generation → Research → Plan loop can run (default: 3).
- `MAX_QA_ITERATIONS` — maximum times QA can reject and trigger rework (default: 3).
- `MAX_TOKENS_PER_AGENT` — optional per-agent token budget.
- `STOP_ON_HIGH_COST` — optional flag to pause if estimated cost exceeds a threshold.
- All agent decisions and iteration reasons are logged to `outputs/` and the state store.

## 7. External Data Sources

The **Idea Generation Agent** and **Plan Agent** can search online for the latest news and social-media trends.

- **Web search:** `src/tools/web_search.py` uses DuckDuckGo by default; optionally SerpAPI.
- **Social media:** `src/tools/social_trends.py` supports X (Twitter), Instagram, and Threads.
  - X requires API keys (`X_API_*`) or a RapidAPI key.
  - Instagram and Threads require a RapidAPI key or official API access.
  - If no API keys are configured, social searches fall back to web search.

## 8. LLM Provider

All agents use **Zhipu AI (智谱AI)** models by default, routed through **OpenRouter** using the shared `src/llm_factory.py`.

- **Endpoint:** `https://openrouter.ai/api/v1`
- **Default model:** `z-ai/glm-4.5` (set via `DEFAULT_AGENT_MODEL`)
- **API key:** `OPENAI_API_KEY` (OpenRouter key)
- **Per-agent overrides:** `temperature` and `model` per agent role in `AGENT_OVERRIDES`

To switch to direct Zhipu AI, set `ZHIPU_API_KEY` and `ZHIPU_BASE_URL` instead. The factory will auto-detect the direct configuration.

## 8. Frontend Dashboard

A Next.js frontend in `frontend/` visualizes the agent pipeline:

- **Live Pipeline tab** — interactive graph of all 8 agents, their statuses, and workflow connections, including the Idea Generation → Research → Plan loop and QA → Execution reject loop.
- **Agent detail panel** — click any agent to see its outputs and logs.
- **History tab** — chronological list of past pipeline runs.

Run the frontend locally:

```bash
cd frontend
npm run dev
```

The frontend uses mock orchestration until the backend API is available.

## 9. When This File Must Be Updated

Update this file whenever you:
- Add, remove, or rename an agent stage.
- Change the hand-off contract or artifact naming convention.
- Change the loop logic, approval gates, or autonomous safeguards.
- Change the rules about what an agent may or may not produce.
- Add project-wide constraints (budget, stack, compliance, etc.).
- Change the frontend architecture or agent visualization.
