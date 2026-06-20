"""Shared helpers for agent implementations."""

import logging
import re

from src.llm_factory import TokenBudgetExceeded, create_completion

logger = logging.getLogger(__name__)


def call_llm(agent_id: str, system_prompt: str, user_prompt: str, fallback: str) -> str:
    """Call the LLM and return the generated text.

    If the LLM is unavailable or misconfigured, log a warning and return the
    fallback text so the pipeline can still run deterministically.

    Token/cost budget overruns are re-raised so the orchestrator can stop the
    run rather than silently degrading to fallback text.
    """
    try:
        return create_completion(agent_id, system_prompt, user_prompt)
    except TokenBudgetExceeded:
        raise
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


def ask_agent(agent_id: str, system_prompt: str, user_prompt: str, fallback: str) -> str:
    """Ask another agent role a focused question without writing artifacts.

    This lets agents collaborate: e.g., the Research Agent can ask the Idea
    Generation Agent to clarify the brief, or the Plan Agent can ask the
    Architecture Agent for a quick feasibility note.
    """
    return call_llm(agent_id, system_prompt, user_prompt, fallback)


def parse_thinking_output(text: str) -> tuple[str, str]:
    """Split an LLM response into a thinking section and a final output section.

    Expected format:

        ## Thinking
        <reasoning>

        ## Output
        <final artifact>

    If the ``## Output`` heading is missing, the entire text is returned as
    output and thinking is empty. If ``## Thinking`` is missing, the entire
    text is returned as output.
    """
    # Match ## Thinking ... ## Output
    pattern = re.compile(
        r"^##\s+Thinking\s*\n(.*?)(?:^##\s+Output\s*\n(.*))",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        thinking = match.group(1).strip()
        output = match.group(2).strip()
        return thinking, output

    # If only ## Output is present, treat everything after it as output.
    output_only = re.compile(
        r"^##\s+Output\s*\n(.*)", re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    m = output_only.search(text)
    if m:
        return "", m.group(1).strip()

    return "", text.strip()


def ask_idea_agent(idea_brief: str, question: str) -> str:
    """Ask the Idea Generation Agent to clarify or expand the idea brief."""
    system = (
        "You are the Idea Generation Agent. A downstream agent needs clarification "
        "about the startup idea below. Answer the question concisely and stay focused "
        "on the idea's problem, solution, target customer, and value proposition."
    )
    user = f"Idea brief:\n{idea_brief}\n\nQuestion:\n{question}"
    fallback = f"The idea brief should be refined: {question}"
    return ask_agent("idea-generation", system, user, fallback)


def ask_architecture_agent(execution_plan: str, plan_report: str, question: str) -> str:
    """Ask the Architecture Agent for a quick feasibility / flexibility note."""
    system = (
        "You are the Architecture Agent. The Plan Agent is evaluating a startup idea "
        "and needs a quick technical feasibility or flexibility assessment. Keep the "
        "answer concise; do not produce a full architecture document."
    )
    user = f"Plan report:\n{plan_report}\n\nExecution plan:\n{execution_plan}\n\nQuestion:\n{question}"
    fallback = "The architecture should be kept simple and flexible for the MVP."
    return ask_agent("architecture", system, user, fallback)
