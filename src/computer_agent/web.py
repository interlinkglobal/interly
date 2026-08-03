"""Permission-gated public web access with local-network protections."""

import ipaddress
import json
import socket
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "Interlink/0.1 (+local personal assistant)"
MAX_DOWNLOAD_BYTES = 2_000_000
MAX_PAGE_TEXT = 25_000
MAX_REDIRECTS = 5


class WebAccessError(RuntimeError):
    """A public web request was rejected or failed safely."""


def validate_public_url(url: str) -> str:
    """Require HTTP(S) and reject local, private, and special-purpose addresses."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise WebAccessError("Only complete public http:// or https:// URLs are allowed.")
    if parsed.username or parsed.password:
        raise WebAccessError("URLs containing credentials are not allowed.")

    try:
        addresses = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as error:
        raise WebAccessError(f"Could not resolve the website hostname: {error}") from error

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise WebAccessError("Local, private, and special-purpose network addresses are blocked.")
    return url


def download_public_text(url: str) -> tuple[str, str, str]:
    """Download a small public text response while validating every redirect."""
    current_url = url
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,text/plain,application/json"}
    with httpx.Client(follow_redirects=False, timeout=15.0, headers=headers) as client:
        for _redirect in range(MAX_REDIRECTS + 1):
            validate_public_url(current_url)
            try:
                with client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise WebAccessError("Website returned an invalid redirect.")
                        current_url = str(response.url.join(location))
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").casefold()
                    allowed_types = ("text/", "application/json", "application/xhtml+xml")
                    if not any(allowed in content_type for allowed in allowed_types):
                        raise WebAccessError(f"Unsupported webpage content type: {content_type}")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_DOWNLOAD_BYTES:
                            raise WebAccessError("Webpage exceeded the 2 MB download limit.")
                    encoding = response.encoding or "utf-8"
                    return body.decode(encoding, errors="replace"), str(response.url), content_type
            except httpx.HTTPError as error:
                raise WebAccessError(f"Web request failed: {error}") from error
    raise WebAccessError("Website exceeded the redirect limit.")


def search_web(query: str) -> str:
    """Search the public web through DuckDuckGo's lightweight HTML endpoint."""
    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        html, _final_url, _content_type = download_public_text(search_url)
    except WebAccessError as error:
        return f"Web search failed safely: {error}"
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, str]] = []
    for result in soup.select(".result"):
        link = result.select_one("a.result__a")
        if link is None or not link.get("href"):
            continue
        href = str(link["href"])
        redirect_target = parse_qs(urlparse(href).query).get("uddg")
        if redirect_target:
            href = unquote(redirect_target[0])
        snippet_node = result.select_one(".result__snippet")
        results.append(
            {
                "title": link.get_text(" ", strip=True),
                "url": href,
                "snippet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
            }
        )
        if len(results) == 8:
            break
    if not results:
        return "No web search results were found."
    return json.dumps(results, indent=2, ensure_ascii=False)


def read_webpage(url: str) -> str:
    """Extract readable text from one public webpage."""
    try:
        body, final_url, content_type = download_public_text(url)
    except WebAccessError as error:
        return f"Webpage read failed safely: {error}"
    if "html" in content_type:
        soup = BeautifulSoup(body, "html.parser")
        for unwanted in soup(["script", "style", "noscript", "svg"]):
            unwanted.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else "Untitled page"
        text = "\n".join(
            line.strip() for line in soup.get_text("\n").splitlines() if line.strip()
        )
    else:
        title = "Text response"
        text = body
    if len(text) > MAX_PAGE_TEXT:
        text = text[:MAX_PAGE_TEXT] + "\n[Page text truncated by Interlink]"
    return f"Final URL: {final_url}\nTitle: {title}\n\n{text}"
