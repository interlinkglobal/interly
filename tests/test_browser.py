from pathlib import Path
from unittest.mock import patch

from computer_agent.browser import IsolatedBrowser


class FakeMouse:
    def __init__(self) -> None:
        self.last_wheel: tuple[int, int] | None = None

    def wheel(self, x: int, y: int) -> None:
        self.last_wheel = (x, y)


class FakeLocator:
    def inner_text(self, timeout: int) -> str:
        assert timeout == 15_000
        return "Rendered JavaScript content"


class FakePage:
    def __init__(self, url: str = "about:blank", title: str = "Blank") -> None:
        self.url = url
        self._title = title
        self.mouse = FakeMouse()
        self.closed = False

    def goto(self, url: str, **_kwargs: object) -> None:
        self.url = url
        self._title = "Example"

    def title(self) -> str:
        return self._title

    def locator(self, selector: str) -> FakeLocator:
        assert selector == "body"
        return FakeLocator()

    def bring_to_front(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True

    def go_back(self, **_kwargs: object) -> None:
        self.url = "https://example.com/back"

    def go_forward(self, **_kwargs: object) -> None:
        self.url = "https://example.com/forward"


class FakeContext:
    def __init__(self) -> None:
        self.pages = [FakePage()]

    def new_page(self) -> FakePage:
        page = FakePage()
        self.pages.append(page)
        return page


@patch("computer_agent.browser.validate_public_url")
def test_isolated_browser_opens_and_reads_rendered_page(_validate: object) -> None:
    browser = IsolatedBrowser(Path("unused"))
    context = FakeContext()
    browser.ensure_started = lambda: context

    opened = browser.open_url("https://example.com")
    rendered = browser.read_page()

    assert "Example" in opened
    assert "Rendered JavaScript content" in rendered


def test_isolated_browser_tabs_scroll_and_navigation() -> None:
    browser = IsolatedBrowser(Path("unused"))
    context = FakeContext()
    browser.ensure_started = lambda: context
    browser.current_page = lambda: context.pages[0]

    assert '"index": 0' in browser.list_tabs()
    assert "Scrolled down" in browser.scroll("down", 500)
    assert context.pages[0].mouse.last_wheel == (0, 500)
    assert "forward" in browser.navigate("forward")
