"""SQLite-backed state store for pipeline runs."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config import Config


class StateStore:
    def __init__(self, db_path: str = Config.SQLITE_PATH) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    idea TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_agent_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    run_id TEXT REFERENCES runs(id),
                    agent_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    outputs TEXT,
                    logs TEXT,
                    started_at TEXT,
                    completed_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_agent_runs_run_id
                    ON agent_runs(run_id);
                """
            )

    def create_run(self, run_id: str, idea: str, status: str, current_agent_id: str) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO runs (id, idea, status, current_agent_id, created_at, updated_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, idea, status, current_agent_id, now, now, None),
            )

    def update_run(
        self,
        run_id: str,
        status: str,
        current_agent_id: str,
        completed: bool = False,
    ) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            if completed:
                conn.execute(
                    "UPDATE runs SET status = ?, current_agent_id = ?, updated_at = ?, completed_at = ? WHERE id = ?",
                    (status, current_agent_id, now, now, run_id),
                )
            else:
                conn.execute(
                    "UPDATE runs SET status = ?, current_agent_id = ?, updated_at = ?, completed_at = NULL WHERE id = ?",
                    (status, current_agent_id, now, run_id),
                )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                return None
            return dict(row)

    def list_runs(self) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]

    def create_agent_run(
        self,
        agent_run_id: str,
        run_id: str,
        agent_id: str,
        status: str,
    ) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO agent_runs (id, run_id, agent_id, status, started_at) VALUES (?, ?, ?, ?, ?)",
                (agent_run_id, run_id, agent_id, status, now),
            )

    def complete_agent_run(
        self,
        agent_run_id: str,
        status: str,
        outputs: list[str],
        logs: list[dict[str, Any]],
    ) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "UPDATE agent_runs SET status = ?, outputs = ?, logs = ?, completed_at = ? WHERE id = ?",
                (status, json.dumps(outputs), json.dumps(logs), now, agent_run_id),
            )

    def list_agent_runs(self, run_id: str) -> list[dict[str, Any]]:
        """Return all agent runs for a pipeline run, oldest first."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_runs WHERE run_id = ? ORDER BY started_at ASC",
                (run_id,),
            ).fetchall()
            return [dict(row) for row in rows]
