"""Web search tool for agents to gather latest news and trends.

Supports DuckDuckGo out of the box (no API key required).
Can be extended to use SerpAPI, Bing, or Google if API keys are provided.
"""

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = "web"


def search_web(query: str, max_results: int = 5) -> list[SearchResult]:
    """Search the web and return a list of results."""
    # Prefer SerpAPI if configured, otherwise fall back to DuckDuckGo.
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if serpapi_key:
        return _search_serpapi(query, max_results)
    return _search_duckduckgo(query, max_results)


def _search_duckduckgo(query: str, max_results: int) -> list[SearchResult]:
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise ImportError("ddgs is required. Install it: pip install ddgs") from exc

    results: list[SearchResult] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    source="duckduckgo",
                )
            )
    return results


def _search_serpapi(query: str, max_results: int) -> list[SearchResult]:
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY is not set")

    import httpx

    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google",
        "num": max_results,
    }
    response = httpx.get("https://serpapi.com/search", params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    results: list[SearchResult] = []
    for r in data.get("organic_results", [])[:max_results]:
        results.append(
            SearchResult(
                title=r.get("title", ""),
                url=r.get("link", ""),
                snippet=r.get("snippet", ""),
                source="serpapi",
            )
        )
    return results


def fetch_url_text(url: str, max_chars: int = 4000) -> str:
    """Fetch and extract readable text from a URL."""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise ImportError("httpx and beautifulsoup4 are required for URL fetching") from exc

    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script/style tags
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return text[:max_chars]
