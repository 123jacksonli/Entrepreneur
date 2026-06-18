# Architecture Design: Entrepreneur Agent Startup

## 1. Overview

This document describes the architecture for the **Entrepreneur Agent Startup** system: a multi-agent pipeline that helps entrepreneurs generate, refine, research, plan, design, build, test, and validate startup ideas, with a web dashboard for visualization.

The system has two main parts:

1. **Agent Backend** — Python orchestrator that runs the 8-agent pipeline.
2. **Web Frontend** — Next.js dashboard that visualizes the pipeline and run history.

## 2. Tech Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Agent backend | Python 3.11+ | Agent logic, LLM calls, file I/O |
| LLM client | `openai` SDK + Zhipu via OpenRouter | OpenAI-compatible, swappable provider |
| Web framework | FastAPI | Lightweight async API for frontend |
| Real-time updates | Server-Sent Events (SSE) | Push agent status to frontend |
| State storage | SQLite + filesystem | Local-first, no external DB required |
| Frontend | Next.js 14 + TypeScript + Tailwind | Existing dashboard |
| Workflow graph | `@xyflow/react` | Existing pipeline visualization |
| State management | Zustand + SWR | Existing frontend state |

## 3. High-Level System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Frontend (Next.js)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Live Pipeline│  │   History    │  │   Agent Detail Panel │  │
│  │   (React Flow)│  │    (SWR)     │  │      (Zustand)       │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼─────────────────────┼──────────────┘
          │                 │                     │
          └─────────────────┼─────────────────────┘
                            │ HTTP / SSE
┌───────────────────────────▼─────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Run API   │  │  Status API │  │      SSE Endpoint       │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼─────────────────────┼───────────────┘
          │                │                     │
          └────────────────┼─────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────┐
│                      Agent Orchestrator                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ State Machine│  │   Artifact   │  │                      │  │
│  │  (pipeline)  │  │   Manager    │  │                      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼─────────────────────┼──────────────┘
          │                 │                     │
          │   ┌─────────────┴─────────────────────┘   │
          │   │                                       │
          ▼   ▼                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         LLM Factory                              │
│              (OpenAI-compatible client → Zhipu)                  │
└─────────────────────────────────────────────────────────────────┘
```

## 4. Directory Structure

```
Entrepreneur/
├── outputs/                    # Agent artifact outputs
├── agents/                     # Agent specifications (AGENT.md)
├── docs/                       # Documentation
├── frontend/                   # Next.js dashboard
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── types/
│   └── tests/
├── src/                        # Python backend
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── llm_factory.py          # Shared LLM client
│   ├── config.py               # Settings / env loader
│   ├── orchestrator.py         # Pipeline state machine
│   ├── state.py                # SQLite state store
│   ├── artifacts.py            # Artifact read/write
│   ├── tools/                  # External data and git tools
│   │   ├── web_search.py
│   │   ├── social_trends.py
│   │   └── git_ops.py
│   └── agents/                 # Agent implementations
│       ├── __init__.py
│       ├── base.py             # Base agent class
│       ├── idea_generation.py
│       ├── research.py
│       ├── plan.py
│       ├── execution_plan.py
│       ├── architecture.py
│       ├── execution.py
│       ├── test.py
│       └── qa.py
├── scripts/
│   └── verify_zhipu.py
├── tests/                      # Python backend tests
├── .env
├── .env.example
├── requirements.txt
└── AGENTS.md
```

## 5. Backend Architecture

### 5.1 FastAPI App (`src/main.py`)

Endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/runs` | Start a new pipeline run |
| GET | `/runs/{run_id}` | Get run status and artifacts |
| GET | `/runs/{run_id}/events` | SSE stream of agent events |
| GET | `/runs` | List past runs |
| GET | `/health` | Health check |

### 5.2 Orchestrator (`src/orchestrator.py`)

A state machine that drives the pipeline autonomously:

```python
class Orchestrator:
    async def start_run(self, idea: str) -> Run:
        # Autonomous loop: Idea Generation → Research → Plan
        for _ in range(Config.MAX_IDEA_ITERATIONS):
            idea_brief = await self.run_agent("idea-generation", idea)
            research = await self.run_agent("research", idea_brief)
            plan = await self.run_agent("plan", research)

            if plan.decision == "stop":
                return Run(status="stopped")
            if plan.decision == "iterate":
                continue
            break  # approved
        else:
            return Run(status="failed", reason="max idea iterations")

        # 4. Execution Plan
        # 5. Architecture
        # 6. Execution
        # 7. Test
        # 8. QA (loops back to Execution on reject, up to MAX_QA_ITERATIONS)
```

- Each stage is an async function.
- Between stages, state is persisted to SQLite.
- Events are emitted via an in-memory queue consumed by the SSE endpoint.
- The Plan Agent is the only approval gate; once approved, execution proceeds automatically.
- `MAX_IDEA_ITERATIONS` and `MAX_QA_ITERATIONS` prevent infinite loops.
- Execution Agent creates a dedicated branch per run and never commits to `main`.

### 5.7 Git Operations (`src/tools/git_ops.py`)

- Creates a new branch per run: `exec/{run_id}` (configurable via `EXEC_BRANCH_PREFIX`).
- Commits and pushes each milestone to the run branch.
- Supports GitHub MCP and git CLI fallback.
- After QA accepts, the branch can be merged into `main` (future enhancement).

### 5.9 External Data Tools (`src/tools/`)

- `web_search.py` — DuckDuckGo/SerpAPI search for news and web pages.
- `social_trends.py` — X/Instagram/Threads trend search with API-key fallback to web search.
- Used by **Idea Generation Agent** and **Plan Agent** to incorporate latest trends.

Required environment variables (optional):

- `SERPAPI_API_KEY` — for Google search via SerpAPI.
- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` — for X API v2.
- `RAPIDAPI_KEY` — for Instagram/Threads/X alternatives.

### 5.3 Base Agent (`src/agents/base.py`)

```python
class BaseAgent(ABC):
    id: str
    name: str

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        ...
```

- Reads prior artifacts from `context.artifacts`.
- Calls `llm_factory.create_completion`.
- Writes output artifact to `outputs/`.
- Returns structured result with status, outputs, and logs.

### 5.4 State Store (`src/state.py`)

SQLite tables:

```sql
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    idea TEXT NOT NULL,
    status TEXT NOT NULL,
    current_agent_id TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE agent_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES runs(id),
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    outputs TEXT,  -- JSON list
    logs TEXT,     -- JSON list
    started_at TEXT,
    completed_at TEXT
);
```

### 5.5 Artifact Manager (`src/artifacts.py`)

- Reads/writes markdown files in `outputs/`.
- Enforces naming convention from `AGENTS.md`.
- Provides `load_artifact(stage)` helper.

### 5.6 Idea Approval Gate

The **Plan Agent** acts as the first approval gate:

- Runs after Research Agent.
- Decisions: `approve`, `iterate`, `stop`.
- If `iterate`, the orchestrator loops back to Idea Generation.
- Only approved ideas proceed to Execution Plan.



## 6. Frontend Architecture

Already implemented in `frontend/`.

### 6.1 Data Flow

1. User clicks **Run Pipeline**.
2. `page.tsx` calls `POST /runs` on the backend.
3. Frontend connects to `/runs/{run_id}/events` via SSE.
4. Each SSE event updates the Zustand store.
5. `PipelineGraph`, `AgentNode`, and `AgentDetailPanel` re-render from store.
6. On run complete, `HistoryTab` refreshes via SWR.

### 6.2 API Client (`frontend/lib/api.ts`)

Replace localStorage with real backend calls:

```typescript
export async function startRun(idea: string): Promise<RunRecord> { ... }
export async function fetchRuns(): Promise<RunRecord[]> { ... }
export async function fetchRun(id: string): Promise<RunRecord> { ... }
export async function approveRun(id: string): Promise<void> { ... }
```

### 6.3 Real-Time Updates

Add an SSE hook:

```typescript
export function useRunEvents(runId: string, onEvent: (event: PipelineEvent) => void) {
  useEffect(() => {
    const source = new EventSource(`/api/runs/${runId}/events`);
    source.onmessage = (msg) => onEvent(JSON.parse(msg.data));
    return () => source.close();
  }, [runId, onEvent]);
}
```

## 7. API Contracts

### Start Run

**Request:**
```json
POST /runs
{
  "idea": "A subscription box for indoor plants"
}
```

**Response:**
```json
{
  "id": "run-1718755200",
  "idea": "A subscription box for indoor plants",
  "status": "running",
  "current_agent_id": "idea-generation",
  "created_at": "2024-06-19T00:00:00Z"
}
```

### SSE Event

```json
data: {
  "type": "agent-start",
  "run_id": "run-1718755200",
  "agent_id": "research",
  "timestamp": "2024-06-19T00:00:01Z"
}
```

### Approve Checkpoint

```json
POST /runs/run-1718755200/approve
{
  "decision": "approve",
  "notes": "Proceed with execution"
}
```

## 8. Deployment

### Local Development

```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload

# Frontend
cd frontend
npm run dev
```

### Production

- Backend: containerized with Docker, run with Uvicorn + Gunicorn.
- Frontend: static export or Vercel/Node server.
- SQLite: mount a persistent volume.

## 9. Non-Functional Requirements

- **Reliability:** Orchestrator persists state after every agent stage so runs can resume after crashes.
- **Observability:** Every agent writes logs; SSE provides real-time visibility.
- **Security:** API keys in `.env`, never committed.
- **Extensibility:** New agents can be added by subclassing `BaseAgent` and updating the orchestrator.
- **Human oversight:** Checkpoint cannot be bypassed programmatically.

## 10. Open Questions

1. Should the backend support multiple concurrent runs, or one at a time?
2. Should agent outputs be versioned per iteration?
3. Should the frontend poll fallback if SSE is unavailable?
