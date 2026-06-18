# Architecture Design: Entrepreneur Agent Startup

## 1. Overview

This document describes the architecture for the **Entrepreneur Agent Startup** system: a multi-agent pipeline that helps entrepreneurs research, plan, design, build, test, and validate startup ideas, with a web dashboard for visualization and a mandatory human-in-the-loop checkpoint.

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
│  │ State Machine│  │   Artifact   │  │   Human Checkpoint   │  │
│  │  (pipeline)  │  │   Manager    │  │      (blocking)      │  │
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
│   ├── checkpoint.py           # Human-in-the-loop gate
│   └── agents/                 # Agent implementations
│       ├── __init__.py
│       ├── base.py             # Base agent class
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
| POST | `/runs/{run_id}/approve` | Human approval to proceed past checkpoint |
| GET | `/health` | Health check |

### 5.2 Orchestrator (`src/orchestrator.py`)

A state machine that drives the pipeline:

```python
class Orchestrator:
    async def start_run(self, idea: str) -> Run:
        # 1. Research
        # 2. Plan
        # 3. Execution Plan
        # 4. Architecture
        # 5. Human checkpoint (block)
        # 6. Execution
        # 7. Test
        # 8. QA
```

- Each stage is an async function.
- Between stages, state is persisted to SQLite.
- Events are emitted via an in-memory queue consumed by the SSE endpoint.
- On human checkpoint, the orchestrator waits on an `asyncio.Event` until `/approve` is called.

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

### 5.6 Human Checkpoint (`src/checkpoint.py`)

- Raised after Architecture Agent completes.
- Blocks orchestrator until `POST /runs/{run_id}/approve` is called.
- Supports: `approve`, `reject`, `iterate`.

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
  "current_agent_id": "research",
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
