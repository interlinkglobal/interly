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


class FakeControl:
    def __init__(self) -> None:
        self.clicked = False
        self.value = ""

    def is_visible(self) -> bool:
        return True

    def evaluate(self, _script: str) -> str:
        return "button"

    def inner_text(self, timeout: int) -> str:
        assert timeout == 2_000
        return "Continue"

    def get_attribute(self, name: str) -> str | None:
        return "Continue" if name == "aria-label" else None

    def click(self, timeout: int) -> None:
        assert timeout == 15_000
        self.clicked = True

    def fill(self, text: str, timeout: int) -> None:
        assert timeout == 15_000
        self.value = text


class FakeControls:
    def __init__(self) -> None:
        self.items = [FakeControl()]

    def count(self) -> int:
        return len(self.items)

    def nth(self, index: int) -> FakeControl:
        return self.items[index]


class FakePage:
    def __init__(self, url: str = "about:blank", title: str = "Blank") -> None:
        self.url = url
        self._title = title
        self.mouse = FakeMouse()
        self.closed = False
        self.controls = FakeControls()

    def goto(self, url: str, **_kwargs: object) -> None:
        self.url = url
        self._title = "Example"

    def title(self) -> str:
        return self._title

    def locator(self, selector: str) -> FakeLocator | FakeControls:
        if selector == "body":
            return FakeLocator()
        return self.controls

    def screenshot(self, path: str, full_page: bool) -> None:
        assert not full_page
        Path(path).write_bytes(b"png")

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


def test_isolated_browser_inspects_clicks_types_and_screenshots(tmp_path: Path) -> None:
    browser = IsolatedBrowser(Path("unused"))
    page = FakePage("https://example.com", "Example")
    browser.current_page = lambda: page
    destination = tmp_path / "page.png"

    assert '"control_id": 0' in browser.inspect_controls()
    assert "Clicked" in browser.click_control(0)
    assert page.controls.items[0].clicked
    assert "Typed" in browser.type_text(0, "hello")
    assert page.controls.items[0].value == "hello"
    assert "Saved" in browser.screenshot(str(destination))
    assert destination.exists()
