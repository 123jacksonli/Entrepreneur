"""Shared helpers for agent implementations."""

import logging
import re

from src.llm_factory import create_completion

logger = logging.getLogger(__name__)


def call_llm(agent_id: str, system_prompt: str, user_prompt: str, fallback: str) -> str:
    """Call the LLM and return the generated text.

    If the LLM is unavailable or misconfigured, log a warning and return the
    fallback text so the pipeline can still run deterministically.
    """
    try:
        return create_completion(agent_id, system_prompt, user_prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM call failed for %s: %s. Using fallback.", agent_id, exc)
        return fallback


def parse_decision(
    text: str,
    valid: tuple[str, ...],
    default: str,
    label: str = "Decision",
) -> str:
    """Parse a structured decision line from an LLM artifact.

    Looks for lines like ``Decision: approve`` or ``Verdict: reject``.
    """
    pattern = re.compile(rf"^{label}:\s*(\w[\w\s]*\w)", re.IGNORECASE | re.MULTILINE)
    for match in pattern.finditer(text):
        decision = match.group(1).strip().lower()
        if decision in valid:
            return decision
    return default
