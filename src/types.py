"""Shared Python types for the backend."""

from typing import Literal

AgentStatus = Literal["idle", "running", "completed", "failed", "waiting"]


class AgentLogEntry(dict):
    timestamp: str
    level: Literal["info", "warn", "error"]
    message: str
