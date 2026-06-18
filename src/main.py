"""FastAPI backend entry point."""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.orchestrator import Orchestrator, PipelineEvent


orchestrator = Orchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    shutdown_event = asyncio.Event()
    scheduler_task: asyncio.Task | None = None

    if orchestrator.config.ENABLE_SCHEDULER:
        scheduler_task = asyncio.create_task(
            _scheduled_run_loop(orchestrator, shutdown_event)
        )

    yield

    shutdown_event.set()
    if scheduler_task:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


async def _scheduled_run_loop(
    orchestrator: Orchestrator, shutdown: asyncio.Event
) -> None:
    """Start one scheduled pipeline run every SCHEDULE_INTERVAL_HOURS."""
    interval = 3600 * orchestrator.config.SCHEDULE_INTERVAL_HOURS
    while not shutdown.is_set():
        try:
            await asyncio.wait_for(shutdown.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
        if shutdown.is_set():
            break

        run_id = f"run-{uuid.uuid4().hex[:8]}"
        idea = orchestrator.config.SCHEDULED_IDEA
        orchestrator.state.create_run(run_id, idea, "running", "idea-generation")
        asyncio.create_task(orchestrator.start_run(run_id, idea))


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
    """Start a new pipeline run in the background."""
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    orchestrator.state.create_run(run_id, idea, "running", "idea-generation")
    asyncio.create_task(orchestrator.start_run(run_id, idea))
    return {"id": run_id, "idea": idea, "status": "running"}


@app.post("/runs/{run_id}/stop")
async def stop_run(run_id: str) -> dict:
    """Request that the running pipeline stop after the current agent finishes."""
    orchestrator.request_stop(run_id)
    return {"id": run_id, "status": "stop_requested"}


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
    """SSE stream of pipeline events for a run."""

    async def event_generator():
        async for event in orchestrator.event_stream(run_id):
            yield event

    return StreamingResponse(event_generator(), media_type="text/event-stream")
