"""Isolated Playwright browser used only when direct HTTP is insufficient."""

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext, Playwright, sync_playwright

from computer_agent.config import config_file
from computer_agent.web import validate_public_url

MAX_BROWSER_TEXT = 25_000


class IsolatedBrowser:
    """Manage one persistent, isolated Chromium-based browser context."""

    def __init__(self, profile_directory: Path | None = None) -> None:
        self.profile_directory = profile_directory or config_file().parent / "browser-profile"
        self.playwright: Playwright | None = None
        self.context: BrowserContext | None = None
        self.active_tab = 0

    def ensure_started(self) -> BrowserContext:
        if self.context is None:
            self.profile_directory.mkdir(parents=True, exist_ok=True)
            self.playwright = sync_playwright().start()
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.profile_directory,
                channel="msedge",
                headless=False,
            )
            if not self.context.pages:
                self.context.new_page()
        return self.context

    def current_page(self) -> Any:
        context = self.ensure_started()
        if self.active_tab >= len(context.pages):
            self.active_tab = max(0, len(context.pages) - 1)
        return context.pages[self.active_tab]

    def open_url(self, url: str) -> str:
        validate_public_url(url)
        context = self.ensure_started()
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        self.active_tab = context.pages.index(page)
        return f"Opened isolated browser tab {self.active_tab}: {page.title()} ({page.url})"

    def read_page(self) -> str:
        page = self.current_page()
        text = page.locator("body").inner_text(timeout=15_000)
        if len(text) > MAX_BROWSER_TEXT:
            text = text[:MAX_BROWSER_TEXT] + "\n[Browser text truncated by Interly]"
        return f"URL: {page.url}\nTitle: {page.title()}\n\n{text}"

    def list_tabs(self) -> str:
        context = self.ensure_started()
        tabs = [
            {"index": index, "active": index == self.active_tab, "title": page.title(), "url": page.url}
            for index, page in enumerate(context.pages)
        ]
        return json.dumps(tabs, indent=2)

    def switch_tab(self, index: int) -> str:
        context = self.ensure_started()
        if index < 0 or index >= len(context.pages):
            return f"No browser tab exists at index {index}."
        self.active_tab = index
        context.pages[index].bring_to_front()
        return f"Switched to tab {index}: {context.pages[index].title()}"

    def close_tab(self, index: int) -> str:
        context = self.ensure_started()
        if index < 0 or index >= len(context.pages):
            return f"No browser tab exists at index {index}."
        context.pages[index].close()
        self.active_tab = max(0, min(self.active_tab, len(context.pages) - 1))
        return f"Closed browser tab {index}."

    def scroll(self, direction: str, amount: int) -> str:
        delta = abs(amount) if direction == "down" else -abs(amount)
        self.current_page().mouse.wheel(0, delta)
        return f"Scrolled {direction} by {abs(amount)} pixels."

    def navigate(self, action: str) -> str:
        page = self.current_page()
        if action == "back":
            page.go_back(wait_until="domcontentloaded", timeout=30_000)
        elif action == "forward":
            page.go_forward(wait_until="domcontentloaded", timeout=30_000)
        else:
            return f"Unknown navigation action: {action}"
        return f"Navigated {action}. Current URL: {page.url}"

    def close(self) -> None:
        if self.context is not None:
            self.context.close()
            self.context = None
        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None


BROWSER = IsolatedBrowser()
