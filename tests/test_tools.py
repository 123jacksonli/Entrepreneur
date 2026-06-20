import pytest

from src.tools.web_search import SearchResult, search_web
from src.tools.social_trends import SocialTrendClient, SocialPost


def test_search_web_returns_list(monkeypatch):
    # Avoid relying on flaky network/SSL in CI by stubbing the DuckDuckGo path.
    def _fake_search(query, max_results):
        return [
            SearchResult(title="Demo", url="https://example.com/ai", snippet="Demo"),
        ]

    monkeypatch.setattr("src.tools.web_search._search_duckduckgo", _fake_search)
    results = search_web("open source AI agents 2024", max_results=3)
    assert isinstance(results, list)
    assert len(results) <= 3
    for r in results:
        assert isinstance(r, SearchResult)
        assert r.url.startswith("http")


def test_social_trend_client_fallback(monkeypatch):
    # Stub web search so the test does not depend on live network access.
    def _fake_search(query, max_results):
        return [SearchResult(title="Demo", url="https://x.com/demo", snippet="Demo post")]

    monkeypatch.setattr("src.tools.social_trends.search_web", _fake_search)
    client = SocialTrendClient()
    posts = client.search_x("AI startup", max_results=2)
    assert isinstance(posts, list)
    assert len(posts) <= 2
    for p in posts:
        assert isinstance(p, SocialPost)
        assert p.platform in ("x", "twitter")
