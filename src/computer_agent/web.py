"""Permission-gated public web access with local-network protections."""

import hashlib
import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "Interlink/0.1 (+local personal assistant)"
MAX_DOWNLOAD_BYTES = 2_000_000
MAX_PAGE_TEXT = 25_000
MAX_REDIRECTS = 5
MAX_FILE_DOWNLOAD_BYTES = 1_000_000_000


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


def download_public_file(url: str, destination: str) -> str:
    """Stream one direct public file URL to an explicit path without overwriting."""
    target = Path(destination).expanduser().resolve()
    if target.exists():
        return f"Destination already exists; nothing was downloaded: {target}"
    if not target.name:
        return "A destination filename is required."

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.interly-download")
    if temporary.exists():
        return f"Temporary download already exists; remove it before retrying: {temporary}"

    current_url = url
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    try:
        with httpx.Client(follow_redirects=False, timeout=30.0, headers=headers) as client:
            for _redirect in range(MAX_REDIRECTS + 1):
                validate_public_url(current_url)
                with client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise WebAccessError("Server returned an invalid redirect.")
                        current_url = str(response.url.join(location))
                        continue

                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if content_type.casefold() in {"text/html", "application/xhtml+xml"}:
                        raise WebAccessError(
                            "The URL returned a webpage, not a direct file. Use the exposed file URL."
                        )
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > MAX_FILE_DOWNLOAD_BYTES:
                        raise WebAccessError("File exceeds Interly's 1 GB download limit.")

                    digest = hashlib.sha256()
                    downloaded = 0
                    with temporary.open("xb") as output:
                        for chunk in response.iter_bytes():
                            downloaded += len(chunk)
                            if downloaded > MAX_FILE_DOWNLOAD_BYTES:
                                raise WebAccessError("File exceeds Interly's 1 GB download limit.")
                            digest.update(chunk)
                            output.write(chunk)
                    temporary.replace(target)
                    return (
                        f"Downloaded file to {target}\n"
                        f"Final URL: {response.url}\n"
                        f"Content type: {content_type or 'unknown'}\n"
                        f"Bytes: {downloaded}\n"
                        f"SHA-256: {digest.hexdigest()}"
                    )
            raise WebAccessError("File URL exceeded the redirect limit.")
    except (httpx.HTTPError, OSError, ValueError, WebAccessError) as error:
        temporary.unlink(missing_ok=True)
        return f"Download failed safely: {error}"


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


def research_web(query: str) -> str:
    """Run two searches, deduplicate URLs, and rank sources with transparent heuristics."""
    variants = [query, f"{query} official reliable sources"]
    collected: dict[str, dict[str, object]] = {}
    for variant in variants:
        raw_results = search_web(variant)
        try:
            results = json.loads(raw_results)
        except json.JSONDecodeError:
            continue
        for result in results:
            url = str(result.get("url", ""))
            parsed = urlparse(url)
            canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").casefold()
            if not canonical:
                continue
            host = (parsed.hostname or "").casefold()
            score = 50
            reasons: list[str] = []
            if parsed.scheme == "https":
                score += 5
                reasons.append("HTTPS")
            if host.endswith((".gov", ".gov.za", ".edu", ".ac.za")):
                score += 25
                reasons.append("government or academic domain")
            if any(marker in host for marker in ("wikipedia.org", "reuters.com", "apnews.com")):
                score += 10
                reasons.append("established reference or news domain")
            collected.setdefault(
                canonical,
                {
                    **result,
                    "quality_score": min(score, 100),
                    "quality_reasons": reasons or ["general public source"],
                },
            )
    ranked = sorted(collected.values(), key=lambda item: int(item["quality_score"]), reverse=True)
    if not ranked:
        return "Multi-source research found no usable results."
    return json.dumps(ranked[:12], indent=2, ensure_ascii=False)
