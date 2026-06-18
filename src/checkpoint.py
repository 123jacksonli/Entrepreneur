"""Human-in-the-loop checkpoint."""

import asyncio
from dataclasses import dataclass
from enum import Enum


class CheckpointDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ITERATE = "iterate"


@dataclass
class CheckpointResult:
    decision: CheckpointDecision
    notes: str = ""


class HumanCheckpoint:
    def __init__(self) -> None:
        self._event = asyncio.Event()
        self._result: CheckpointResult | None = None

    async def wait(self) -> CheckpointResult:
        await self._event.wait()
        assert self._result is not None
        return self._result

    def resolve(self, result: CheckpointResult) -> None:
        self._result = result
        self._event.set()

    def reset(self) -> None:
        self._event.clear()
        self._result = None
