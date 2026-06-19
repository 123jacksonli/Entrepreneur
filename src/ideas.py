"""Idea generation helpers for autonomous pipeline runs.

When no human idea is provided, the system can generate one by combining the
latest web/social trend signals with an LLM prompt.
"""

import logging
import random

from src.llm_factory import create_completion
from src.tools.social_trends import SocialTrendClient
from src.tools.web_search import search_web

logger = logging.getLogger(__name__)

FALLBACK_IDEAS = [
    "Build an AI assistant that turns noisy customer support tickets into prioritized action items.",
    "Create a micro-SaaS that automatically generates weekly SEO-optimized blog posts for niche e-commerce stores.",
    "Design a tool that scrapes public government contract opportunities and matches them to small SaaS vendors.",
    "Build a personal finance app that predicts cash-flow gaps for freelancers using their invoice history.",
    "Create a no-code platform that turns API documentation into interactive developer portals.",
]


def generate_idea() -> str:
    """Generate a fresh SaaS idea using live trend signals and the LLM.

    Falls back to a curated list if the LLM is unavailable.
    """
    trend_signals: list[str] = []
    try:
        web_results = search_web("SaaS startup trends 2024 2025", max_results=5)
        for r in web_results:
            trend_signals.append(f"- {r.title}: {r.snippet}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Trend search failed during idea generation: %s", exc)

    try:
        social_client = SocialTrendClient()
        social_posts = social_client.search_all("SaaS startup idea", max_results=5)
        for p in social_posts:
            trend_signals.append(f"- {p.platform}: {p.text[:200]}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Social trend search failed during idea generation: %s", exc)

    system_prompt = (
        "You are an expert startup ideator. Based on the latest trend signals below, "
        "invent one concrete, bootstrappable SaaS idea. Return only the idea as a "
        "single paragraph: problem, solution, and target customer. Be specific."
    )
    user_prompt = f"Latest signals:\n{chr(10).join(trend_signals)}\n\nGenerate one SaaS idea."

    try:
        return create_completion("idea-generation", system_prompt, user_prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM idea generation failed: %s. Using fallback.", exc)
        return random.choice(FALLBACK_IDEAS)
