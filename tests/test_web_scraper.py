from src.tools.web_scraper import extract_text, scrape_url


def test_extract_text_strips_scripts_and_styles():
    html = """
    <html>
      <head><title>Test Page</title></head>
      <body>
        <nav>Home | About</nav>
        <script>alert('x')</script>
        <style>.x{}</style>
        <article>
          <h1>Hello World</h1>
          <p>This is the content.</p>
        </article>
        <footer>Footer text</footer>
      </body>
    </html>
    """
    title, text = extract_text(html)
    assert title == "Test Page"
    assert "Hello World" in text
    assert "This is the content." in text
    assert "alert" not in text
    assert ".x{}" not in text
    assert "Footer text" not in text


def test_extract_text_truncates_to_max_length():
    html = "<html><body><p>" + "word " * 1000 + "</p></body></html>"
    title, text = extract_text(html, max_length=100)
    assert len(text) <= 105  # includes ellipsis
    assert text.endswith("…")


def test_scrape_url_handles_unreachable_domain():
    page = scrape_url("http://localhost:59999/no-such-page", timeout=1.0)
    assert page.url == "http://localhost:59999/no-such-page"
    assert page.title == ""
    assert page.text == ""
