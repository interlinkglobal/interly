import hashlib
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from computer_agent.web import (
    WebAccessError,
    download_public_file,
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


def test_download_public_file_streams_and_reports_hash(tmp_path: Path) -> None:
    body = b"basic mp4 bytes"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "video/mp4", "content-length": str(len(body))},
            content=body,
            request=request,
        )
    )
    destination = tmp_path / "video.mp4"

    with (
        patch("computer_agent.web.validate_public_url", return_value="https://example.com/video.mp4"),
        patch("computer_agent.web.httpx.Client", return_value=httpx.Client(transport=transport)),
    ):
        result = download_public_file("https://example.com/video.mp4", str(destination))

    assert destination.read_bytes() == body
    assert "Content type: video/mp4" in result
    assert f"SHA-256: {hashlib.sha256(body).hexdigest()}" in result


def test_download_public_file_refuses_overwrite(tmp_path: Path) -> None:
    destination = tmp_path / "existing.mp4"
    destination.write_bytes(b"keep me")

    result = download_public_file("https://example.com/video.mp4", str(destination))

    assert "already exists" in result
    assert destination.read_bytes() == b"keep me"


def test_download_public_file_rejects_webpage(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<html>not a file</html>",
            request=request,
        )
    )
    destination = tmp_path / "wrong.mp4"

    with (
        patch("computer_agent.web.validate_public_url", return_value="https://example.com/watch"),
        patch("computer_agent.web.httpx.Client", return_value=httpx.Client(transport=transport)),
    ):
        result = download_public_file("https://example.com/watch", str(destination))

    assert "returned a webpage" in result
    assert not destination.exists()
