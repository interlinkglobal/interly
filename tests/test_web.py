from unittest.mock import patch

import pytest

from computer_agent.web import (
    WebAccessError,
    read_webpage,
    research_web,
    search_web,
    validate_public_url,
)


def test_localhost_is_blocked_before_request() -> None:
    with pytest.raises(WebAccessError, match="private"):
        validate_public_url("http://127.0.0.1/admin")


@patch("computer_agent.web.download_public_text")
def test_search_extracts_titles_and_direct_urls(download: object) -> None:
    download.return_value = (
        '<div class="result"><a class="result__a" href="https://example.com">Example</a><div class="result__snippet">A result.</div></div>',
        "https://html.duckduckgo.com/html/",
        "text/html",
    )

    result = search_web("example")

    assert '"title": "Example"' in result
    assert '"url": "https://example.com"' in result


@patch("computer_agent.web.download_public_text")
def test_webpage_reader_removes_scripts(download: object) -> None:
    download.return_value = (
        "<html><title>Page</title><script>malicious()</script><p>Useful text</p></html>",
        "https://example.com",
        "text/html",
    )

    result = read_webpage("https://example.com")

    assert "Useful text" in result
    assert "malicious" not in result


@patch("computer_agent.web.search_web")
def test_research_deduplicates_and_scores_sources(search: object) -> None:
    search.return_value = (
        '[{"title":"Gov","url":"https://example.gov.za/report","snippet":"One"},'
        '{"title":"Duplicate","url":"https://example.gov.za/report?tracking=1","snippet":"Two"}]'
    )

    result = research_web("example")

    assert result.count('"url"') == 1
    assert '"quality_score": 80' in result
