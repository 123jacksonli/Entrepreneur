"""Social media trend tools for agents.

Requires API keys for live data. Falls back to web search for public posts if
no social API key is configured.
"""

import os
from dataclasses import dataclass
from typing import Any

from src.tools.web_search import search_web


@dataclass
class SocialPost:
    platform: str
    author: str
    text: str
    url: str
    engagement: str | None = None


class SocialTrendClient:
    """Unified client for fetching trends from X, Instagram, and Threads."""

    def __init__(self) -> None:
        self.x_api_key = os.getenv("X_API_KEY")
        self.x_api_secret = os.getenv("X_API_SECRET")
        self.x_access_token = os.getenv("X_ACCESS_TOKEN")
        self.x_access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")

    def search_x(self, query: str, max_results: int = 5) -> list[SocialPost]:
        """Search X (Twitter). Requires X API keys or RapidAPI key."""
        if self.x_api_key and self.x_api_secret:
            return self._search_x_official(query, max_results)
        if self.rapidapi_key:
            return self._search_x_rapidapi(query, max_results)
        return self._fallback_web_search("x twitter", query, max_results)

    def search_instagram(self, query: str, max_results: int = 5) -> list[SocialPost]:
        """Search Instagram. Requires official API or RapidAPI key."""
        if self.rapidapi_key:
            return self._search_instagram_rapidapi(query, max_results)
        return self._fallback_web_search("instagram", query, max_results)

    def search_threads(self, query: str, max_results: int = 5) -> list[SocialPost]:
        """Search Threads. Requires official API or RapidAPI key."""
        if self.rapidapi_key:
            return self._search_threads_rapidapi(query, max_results)
        return self._fallback_web_search("threads", query, max_results)

    def _search_x_official(self, query: str, max_results: int) -> list[SocialPost]:
        try:
            import tweepy
        except ImportError as exc:
            raise ImportError("tweepy is required for X API v2. Install it: pip install tweepy") from exc

        client = tweepy.Client(
            consumer_key=self.x_api_key,
            consumer_secret=self.x_api_secret,
            access_token=self.x_access_token,
            access_token_secret=self.x_access_token_secret,
        )
        tweets = client.search_recent_tweets(query=query, max_results=max_results, tweet_fields=["public_metrics"])
        results: list[SocialPost] = []
        for tweet in tweets.data or []:
            metrics = tweet.public_metrics or {}
            results.append(
                SocialPost(
                    platform="x",
                    author=tweet.author_id or "unknown",
                    text=tweet.text,
                    url=f"https://x.com/i/web/status/{tweet.id}",
                    engagement=f"likes={metrics.get('like_count', 0)}, retweets={metrics.get('retweet_count', 0)}",
                )
            )
        return results

    def _search_x_rapidapi(self, query: str, max_results: int) -> list[SocialPost]:
        # Placeholder for RapidAPI integration.
        return self._fallback_web_search("x twitter", query, max_results)

    def _search_instagram_rapidapi(self, query: str, max_results: int) -> list[SocialPost]:
        # Placeholder for RapidAPI integration.
        return self._fallback_web_search("instagram", query, max_results)

    def _search_threads_rapidapi(self, query: str, max_results: int) -> list[SocialPost]:
        # Placeholder for RapidAPI integration.
        return self._fallback_web_search("threads", query, max_results)

    def _fallback_web_search(self, platform: str, query: str, max_results: int) -> list[SocialPost]:
        """Fallback: search the web for public posts on the platform."""
        results = search_web(f"site:{platform.split()[0]} {query}", max_results=max_results)
        return [
            SocialPost(
                platform=platform.split()[0],
                author="unknown",
                text=r.snippet,
                url=r.url,
            )
            for r in results
        ]
