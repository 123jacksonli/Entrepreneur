"""Shared LLM client factory for the Entrepreneur Agent Startup.

All agents call Zhipu AI models through OpenRouter using the OpenAI-compatible
endpoint. The provider can be switched to direct Zhipu AI by setting
ZHIPU_API_KEY and ZHIPU_BASE_URL instead of OPENAI_API_KEY and OPENAI_BASE_URL.
"""

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_MODEL = os.getenv("DEFAULT_AGENT_MODEL", "z-ai/glm-4.5")

# Support both OpenRouter and direct Zhipu configuration.
if os.getenv("ZHIPU_API_KEY"):
    API_KEY = os.getenv("ZHIPU_API_KEY")
    BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
else:
    API_KEY = os.getenv("OPENAI_API_KEY")
    BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")

AGENT_OVERRIDES: dict[str, dict[str, Any]] = {
    "idea-generation": {"model": DEFAULT_MODEL, "temperature": 0.4},
    "research": {"model": DEFAULT_MODEL, "temperature": 0.3},
    "plan": {"model": DEFAULT_MODEL, "temperature": 0.3},
    "execution-plan": {"model": DEFAULT_MODEL, "temperature": 0.2},
    "architecture": {"model": DEFAULT_MODEL, "temperature": 0.2},
    "execution": {"model": DEFAULT_MODEL, "temperature": 0.1},
    "test": {"model": DEFAULT_MODEL, "temperature": 0.1},
    "qa": {"model": DEFAULT_MODEL, "temperature": 0.2},
}


def get_client() -> OpenAI:
    """Return a configured OpenAI client for the active provider."""
    if not API_KEY:
        raise ValueError(
            "No API key configured. Set OPENAI_API_KEY (OpenRouter) "
            "or ZHIPU_API_KEY (direct Zhipu) in your .env file."
        )
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


def create_completion(
    agent_id: str,
    system_prompt: str,
    user_prompt: str,
    **kwargs: Any,
) -> str:
    """Call the LLM for a specific agent and return the generated text."""
    client = get_client()
    overrides = AGENT_OVERRIDES.get(agent_id, {})

    response = client.chat.completions.create(
        model=overrides.get("model", DEFAULT_MODEL),
        temperature=overrides.get("temperature", 0.2),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **kwargs,
    )

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError(f"LLM returned empty content for agent {agent_id}")
    return content
