"""Shared LLM client factory for the Entrepreneur Agent Startup.

All agents call Zhipu AI models through OpenRouter using the OpenAI-compatible
endpoint. The provider can be switched to direct Zhipu AI by setting
ZHIPU_API_KEY and ZHIPU_BASE_URL instead of OPENAI_API_KEY and OPENAI_BASE_URL.
"""

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from src.config import Config

load_dotenv()

DEFAULT_MODEL = os.getenv("DEFAULT_AGENT_MODEL", "z-ai/glm-4.5")

# Support Kimi Code, OpenRouter, and direct Zhipu configuration.
# Kimi is preferred when KIMI_API_KEY is set; otherwise OpenRouter/Zhipu.
if os.getenv("KIMI_API_KEY"):
    API_KEY = os.getenv("KIMI_API_KEY")
    BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1")
elif os.getenv("OPENAI_API_KEY"):
    API_KEY = os.getenv("OPENAI_API_KEY")
    BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
elif os.getenv("ZHIPU_API_KEY"):
    API_KEY = os.getenv("ZHIPU_API_KEY")
    BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
else:
    API_KEY = None
    BASE_URL = None


class TokenBudgetExceeded(Exception):
    """Raised when an agent exceeds its token or estimated cost budget."""


# Per-agent-role token counters (in-process). These reset when the process
# restarts; persistent budgeting can be added later via the state store.
_AGENT_TOKEN_COUNTERS: dict[str, int] = {}
_AGENT_ESTIMATED_COST: dict[str, float] = {}

# Rough per-1M-token pricing in USD for cost estimation.
# OpenRouter/Zhipu prices change; these defaults are conservative guardrails.
_MODEL_PRICING: dict[str, dict[str, float]] = {
    "z-ai/glm-4.5": {"prompt": 5.0, "completion": 15.0},
    "z-ai/glm-4.5-flash": {"prompt": 1.0, "completion": 3.0},
    "zhipu/glm-4": {"prompt": 3.5, "completion": 10.5},
    "zhipu/glm-4-flash": {"prompt": 0.5, "completion": 1.5},
    "kimi-coding": {"prompt": 3.0, "completion": 12.0},
    "default": {"prompt": 5.0, "completion": 15.0},
}


def _is_kimi_coding() -> bool:
    return "api.kimi.com/coding" in (BASE_URL or "")


def _model_pricing_key(model: str) -> str:
    if _is_kimi_coding():
        return "kimi-coding"
    return model if model in _MODEL_PRICING else "default"


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _MODEL_PRICING.get(_model_pricing_key(model), _MODEL_PRICING["default"])
    return (
        prompt_tokens * rates["prompt"] + completion_tokens * rates["completion"]
    ) / 1_000_000


AGENT_OVERRIDES: dict[str, dict[str, Any]] = {
    "idea-generation": {"model": DEFAULT_MODEL, "temperature": 0.4},
    "research": {"model": DEFAULT_MODEL, "temperature": 0.3},
    "plan": {"model": DEFAULT_MODEL, "temperature": 0.3},
    "execution-plan": {"model": DEFAULT_MODEL, "temperature": 0.2},
    "architecture": {"model": DEFAULT_MODEL, "temperature": 0.2},
    "execution": {"model": DEFAULT_MODEL, "temperature": 0.1},
    "test": {"model": DEFAULT_MODEL, "temperature": 0.1},
    "qa": {"model": DEFAULT_MODEL, "temperature": 0.2},
    "supabase-design": {"model": DEFAULT_MODEL, "temperature": 0.2},
    "social-media": {"model": DEFAULT_MODEL, "temperature": 0.4},
}


def get_client() -> OpenAI:
    """Return a configured OpenAI client for the active provider."""
    if not API_KEY:
        raise ValueError(
            "No API key configured. Set OPENAI_API_KEY (OpenRouter), "
            "ZHIPU_API_KEY (direct Zhipu), or KIMI_API_KEY in your .env file."
        )
    # Kimi Code Plan requires a coding-agent User-Agent and only supports
    # temperature == 1 for its reasoning models.
    if _is_kimi_coding():
        return OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            default_headers={"User-Agent": "claude-code/0.1.0"},
        )
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


def create_completion(
    agent_id: str,
    system_prompt: str,
    user_prompt: str,
    **kwargs: Any,
) -> str:
    """Call the LLM for a specific agent and return the generated text.

    Enforces ``MAX_TOKENS_PER_AGENT`` (per-call cap + cumulative counter) and
    ``STOP_ON_HIGH_COST`` / ``MAX_ESTIMATED_COST_USD``.
    """
    client = get_client()
    overrides = AGENT_OVERRIDES.get(agent_id, {})
    model = overrides.get("model", DEFAULT_MODEL)

    temperature = overrides.get("temperature", 0.2)
    if _is_kimi_coding():
        temperature = 1

    request_kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    # Per-call token cap.
    if Config.MAX_TOKENS_PER_AGENT:
        request_kwargs["max_tokens"] = Config.MAX_TOKENS_PER_AGENT
    # Allow explicit per-call overrides (e.g., from agents that need more).
    request_kwargs.update(kwargs)

    response = client.chat.completions.create(**request_kwargs)

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError(f"LLM returned empty content for agent {agent_id}")

    # Track token usage and enforce budgets.
    usage = response.usage
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = prompt_tokens + completion_tokens

    _AGENT_TOKEN_COUNTERS[agent_id] = _AGENT_TOKEN_COUNTERS.get(agent_id, 0) + total_tokens
    _AGENT_ESTIMATED_COST[agent_id] = _AGENT_ESTIMATED_COST.get(agent_id, 0.0) + _estimate_cost(
        model, prompt_tokens, completion_tokens
    )

    max_tokens = Config.MAX_TOKENS_PER_AGENT
    if max_tokens and _AGENT_TOKEN_COUNTERS[agent_id] > max_tokens:
        raise TokenBudgetExceeded(
            f"Agent '{agent_id}' exceeded MAX_TOKENS_PER_AGENT "
            f"({_AGENT_TOKEN_COUNTERS[agent_id]} > {max_tokens})"
        )

    if Config.STOP_ON_HIGH_COST and Config.MAX_ESTIMATED_COST_USD is not None:
        if _AGENT_ESTIMATED_COST[agent_id] > Config.MAX_ESTIMATED_COST_USD:
            raise TokenBudgetExceeded(
                f"Agent '{agent_id}' exceeded estimated cost budget "
                f"(${_AGENT_ESTIMATED_COST[agent_id]:.4f} > ${Config.MAX_ESTIMATED_COST_USD:.4f})"
            )

    return content


def reset_budget_counters(agent_id: str | None = None) -> None:
    """Reset token/cost counters. Useful between pipeline runs in tests."""
    if agent_id is None:
        _AGENT_TOKEN_COUNTERS.clear()
        _AGENT_ESTIMATED_COST.clear()
    else:
        _AGENT_TOKEN_COUNTERS.pop(agent_id, None)
        _AGENT_ESTIMATED_COST.pop(agent_id, None)
