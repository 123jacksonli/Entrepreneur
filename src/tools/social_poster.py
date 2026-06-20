"""Social media posting tool.

Posts content to connected social accounts when API keys are configured. If no
keys are available, the tool returns a dry-run log so the Social Media Manager
Agent can still plan and review posts.
"""

import logging
import os
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

Platform = Literal["x", "threads", "linkedin", "reddit"]


@dataclass
class PostResult:
    platform: Platform
    text: str
    posted: bool
    url: str | None = None
    error: str | None = None


def post_to_x(text: str) -> PostResult:
    """Post to X (Twitter) using tweepy if keys are configured."""
    try:
        import tweepy
    except ImportError:
        return PostResult(platform="x", text=text, posted=False, error="tweepy not installed")

    bearer = os.getenv("X_BEARER_TOKEN")
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        return PostResult(platform="x", text=text, posted=False, error="X API keys not configured")

    try:
        client = tweepy.Client(
            bearer_token=bearer,
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
        response = client.create_tweet(text=text[:280])
        tweet_id = response.data["id"] if response.data else None
        url = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else None
        return PostResult(platform="x", text=text, posted=True, url=url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to post to X")
        return PostResult(platform="x", text=text, posted=False, error=str(exc))


def post_to_threads(text: str) -> PostResult:
    """Placeholder for Threads posting."""
    return PostResult(
        platform="threads",
        text=text,
        posted=False,
        error="Threads posting not implemented (requires Meta Graph API)",
    )


def post_to_linkedin(text: str) -> PostResult:
    """Placeholder for LinkedIn posting."""
    return PostResult(
        platform="linkedin",
        text=text,
        posted=False,
        error="LinkedIn posting not implemented (requires LinkedIn API)",
    )


def post_to_reddit(title: str, text: str, subreddit: str = "") -> PostResult:
    """Placeholder for Reddit posting."""
    return PostResult(
        platform="reddit",
        text=text,
        posted=False,
        error="Reddit posting not implemented (requires PRAW and API credentials)",
    )


def publish_posts(posts: list[dict]) -> list[PostResult]:
    """Publish a list of posts.

    Each post dict should have: platform, text, and optional subreddit/title.
    Returns the result of each attempt.
    """
    results: list[PostResult] = []
    for post in posts:
        platform = post.get("platform")
        text = post.get("text", "")
        if platform == "x":
            results.append(post_to_x(text))
        elif platform == "threads":
            results.append(post_to_threads(text))
        elif platform == "linkedin":
            results.append(post_to_linkedin(text))
        elif platform == "reddit":
            results.append(post_to_reddit(post.get("title", ""), text, post.get("subreddit", "")))
        else:
            results.append(PostResult(platform="x", text=text, posted=False, error=f"Unknown platform: {platform}"))
    return results
