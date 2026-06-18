"""FastAPI backend entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.orchestrator import Orchestrator


orchestrator = Orchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(title="Entrepreneur Agent Startup", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/runs")
async def start_run(idea: str) -> dict:
    import uuid

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    # TODO: run orchestrator in background task
    return {"id": run_id, "idea": idea, "status": "running"}


@app.get("/runs")
async def list_runs() -> list[dict]:
    return orchestrator.state.list_runs()


@app.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    run = orchestrator.state.get_run(run_id)
    if not run:
        return {"error": "Run not found"}
    return run


@app.get("/runs/{run_id}/events")
async def run_events(run_id: str):
    from fastapi.responses import StreamingResponse

    async def event_generator():
        async for event in orchestrator.event_stream(run_id):
            yield event

    return StreamingResponse(event_generator(), media_type="text/event-stream")
