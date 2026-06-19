"""Social media trend discovery via web search + scraping.

This module does NOT require X/Meta API keys. It finds social trend signals by
searching public social platforms (X/Twitter, Reddit, Threads, Instagram) and
scraping the result pages for post-like snippets.
"""

import logging
import re
from dataclasses import dataclass

from src.tools.web_scraper import scrape_url
from src.tools.web_search import search_web

logger = logging.getLogger(__name__)


@dataclass
class SocialPost:
    platform: str
    author: str
    text: str
    url: str
    engagement: str | None = None


def _platform_queries(query: str) -> dict[str, str]:
    return {
        "x": f"site:x.com OR site:twitter.com {query}",
        "reddit": f"site:reddit.com {query}",
        "threads": f"site:threads.net {query}",
        "instagram": f"site:instagram.com {query}",
    }


def _extract_posts(html: str, platform: str, url: str, max_results: int) -> list[SocialPost]:
    """Naive post extraction from a social platform HTML page.

    Real social platforms heavily obfuscate their markup and often block
    scrapers, so this is a best-effort fallback. The richer signal usually
    comes from the search-result snippets themselves.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    texts: list[str] = []

    # Try common tweet/post containers.
    selectors = ["article", "[data-testid='tweet']", ".tweet", ".post", ".entry"]
    for selector in selectors:
        for element in soup.select(selector):
            text = element.get_text(separator=" ", strip=True)
            if len(text) > 20:
                texts.append(text)
        if texts:
            break

    if not texts:
        # Fall back to paragraph text.
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 20:
                texts.append(text)

    posts: list[SocialPost] = []
    for text in texts[:max_results]:
        # Truncate very long blobs.
        text = text[:500]
        # Remove engagement counts if they appear inline.
        text = re.sub(r"\d+\s*(likes?|replies?|retweets?|comments?|shares?)", "", text, flags=re.I)
        posts.append(SocialPost(platform=platform, author="", text=text, url=url))
    return posts


class SocialTrendClient:
    """Unified client for fetching social trend signals without API keys."""

    def search_x(self, query: str, max_results: int = 5) -> list[SocialPost]:
        return self._search_platform("x", query, max_results)

    def search_reddit(self, query: str, max_results: int = 5) -> list[SocialPost]:
        return self._search_platform("reddit", query, max_results)

    def search_threads(self, query: str, max_results: int = 5) -> list[SocialPost]:
        return self._search_platform("threads", query, max_results)

    def search_instagram(self, query: str, max_results: int = 5) -> list[SocialPost]:
        return self._search_platform("instagram", query, max_results)

    def search_all(self, query: str, max_results: int = 10) -> list[SocialPost]:
        """Search all supported social platforms and aggregate unique signals."""
        all_posts: list[SocialPost] = []
        per_platform = max(1, max_results // 4)
        for platform in ("reddit", "x", "threads", "instagram"):
            try:
                posts = self._search_platform(platform, query, per_platform)
                all_posts.extend(posts)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Social trend search failed for %s: %s", platform, exc)
        return all_posts[:max_results]

    def _search_platform(
        self, platform: str, query: str, max_results: int
    ) -> list[SocialPost]:
        search_query = _platform_queries(query).get(platform, f"{platform} {query}")
        results = search_web(search_query, max_results=max_results * 2)
        posts: list[SocialPost] = []

        for r in results:
            # Search-result snippet is already a strong signal.
            snippet = r.snippet or ""
            if len(snippet) > 20:
                posts.append(
                    SocialPost(
                        platform=platform,
                        author="",
                        text=snippet[:300],
                        url=r.url,
                    )
                )

            # Try to scrape the page for more posts.
            try:
                page = scrape_url(r.url, max_length=2000, timeout=10.0)
                if page.text:
                    scraped = _extract_posts(page.text, platform, r.url, max_results=2)
                    posts.extend(scraped)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not scrape %s: %s", r.url, exc)

            if len(posts) >= max_results:
                break

        return posts[:max_results]
