# Entrepreneur Agent Startup — Agent Operating Manual

## 1. Project Vision

This repository builds an **agent-driven startup builder** for entrepreneurs. A user describes a business idea (or even just an interest area), and a pipeline of specialized agents refines, researches, plans, designs, builds, tests, and validates startup ideas.

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
└─────────────┘
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
2. **No code before Plan approval.** The Execution Agent is the only agent allowed to write implementation code, and it may only run after the Plan Agent has approved the idea.
3. **Artifacts only.** Idea Generation, Research, Plan, Execution Plan, and Architecture agents produce markdown artifacts, not runnable code.
4. **Hand-off contract.** Each agent must write its output to a clearly named artifact and signal completion to the orchestrator.
5. **Idea loop.** Idea Generation → Research → Plan form a loop. The Plan Agent approves, iterates, or stops. Only approved ideas proceed to Execution Plan.
6. **Iteration is normal.** QA can reject output and send it back to the Execution Agent. Earlier stages can also be revisited if the Plan Agent requests iteration.
7. **Execution Agent uses GitHub MCP.** The Execution Agent must create/select repositories, commit after each milestone, and push changes so all execution output is version-controlled.

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

## 6. LLM Provider

All agents use **Zhipu AI (智谱AI)** models by default, routed through **OpenRouter** using the shared `src/llm_factory.py`.

- **Endpoint:** `https://openrouter.ai/api/v1`
- **Default model:** `z-ai/glm-4.5` (set via `DEFAULT_AGENT_MODEL`)
- **API key:** `OPENAI_API_KEY` (OpenRouter key)
- **Per-agent overrides:** `temperature` and `model` per agent role in `AGENT_OVERRIDES`

To switch to direct Zhipu AI, set `ZHIPU_API_KEY` and `ZHIPU_BASE_URL` instead. The factory will auto-detect the direct configuration.

## 7. Frontend Dashboard

A Next.js frontend in `frontend/` visualizes the agent pipeline:

- **Live Pipeline tab** — interactive graph of all 8 agents, their statuses, and workflow connections, including the Idea Generation → Research → Plan loop.
- **Agent detail panel** — click any agent to see its outputs and logs.
- **History tab** — chronological list of past pipeline runs.

Run the frontend locally:

```bash
cd frontend
npm run dev
```

The frontend uses mock orchestration until the backend API is available.

## 8. When This File Must Be Updated

Update this file whenever you:
- Add, remove, or rename an agent stage.
- Change the hand-off contract or artifact naming convention.
- Change the loop logic or approval gates.
- Change the rules about what an agent may or may not produce.
- Add project-wide constraints (budget, stack, compliance, etc.).
- Change the frontend architecture or agent visualization.
