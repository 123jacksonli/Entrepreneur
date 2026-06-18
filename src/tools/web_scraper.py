"""Web scraping tool for fetching and extracting article-like text from URLs.

Used by the Research and Plan agents to read the content behind search results.
"""

import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ScrapedPage:
    url: str
    title: str
    text: str
    status_code: int | None = None


def _is_absolute(url: str) -> bool:
    return bool(urlparse(url).netloc)


def _normalize_url(base: str, link: str) -> str:
    return urljoin(base, link) if not _is_absolute(link) else link


def extract_text(html: str, max_length: int | None = 5000) -> tuple[str, str]:
    """Extract (title, text) from raw HTML.

    Strips scripts, styles, nav, footer, and other boilerplate to keep the
    article-like content.
    """
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Remove non-content elements.
    for selector in ["script", "style", "nav", "footer", "header", "aside"]:
        for element in soup.find_all(selector):
            element.decompose()

    # Prefer article/main content if available.
    content_tag = soup.find("article") or soup.find("main") or soup.find("body")
    if content_tag is None:
        content_tag = soup

    text = content_tag.get_text(separator="\n", strip=True)
    # Collapse excessive blank lines.
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    if max_length and len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0] + "…"

    return title, text


def scrape_url(url: str, max_length: int | None = 5000, timeout: float = 30.0) -> ScrapedPage:
    """Fetch a URL and return a cleaned text extraction.

    On failure returns a ScrapedPage with empty text and logs the error.
    """
    try:
        response = httpx.get(url, follow_redirects=True, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return ScrapedPage(url=url, title="", text="", status_code=None)

    title, text = extract_text(response.text, max_length=max_length)
    return ScrapedPage(
        url=str(response.url),
        title=title,
        text=text,
        status_code=response.status_code,
    )


def scrape_urls(
    urls: list[str],
    max_length: int | None = 5000,
    timeout: float = 30.0,
) -> list[ScrapedPage]:
    """Scrape a list of URLs and return successful extractions."""
    results = []
    for url in urls:
        page = scrape_url(url, max_length=max_length, timeout=timeout)
        if page.text:
            results.append(page)
    return results
