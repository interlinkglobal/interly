"""Runtime tool registry combining established tools with governance and desktop tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from computer_agent.desktop import (
    capture_screen,
    inspect_visible_controls,
    keyboard_action,
    list_windows,
    mouse_action,
    ocr_image,
    read_clipboard,
    window_action,
    write_clipboard,
)
from computer_agent.documents import SUPPORTED_EXTENSIONS, read_structured_document
from computer_agent.tools import TOOL_SCHEMAS as BASE_TOOL_SCHEMAS
from computer_agent.tools import LocalOnlyResult
from computer_agent.tools import describe_tool as describe_base_tool
from computer_agent.tools import execute_tool as execute_base_tool


def _function(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


BASE_RUNTIME_TOOL_SCHEMAS = [
    schema
    for schema in BASE_TOOL_SCHEMAS
    if schema.get("function", {}).get("name") != "read_text_file"
]

ADDITIONAL_TOOL_SCHEMAS: list[dict[str, Any]] = [
    _function(
        "read_text_file",
        (
            "Read one approved local file. Plain text and source files use the bounded text reader. "
            "PDF, Word (.docx), Excel (.xlsx/.xlsm), and PowerPoint (.pptx) files are parsed "
            "read-only into structured pages/blocks/sheets/slides, headings, tables, formulas, "
            "and metadata where available."
        ),
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    ),
    _function(
        "propose_plan",
        (
            "Present a specific multi-step plan before a request that requires two or more "
            "meaningful tool actions. The host asks the user whether to approve this plan scope."
        ),
        {
            "type": "object",
            "properties": {
                "title": {"type": "string", "maxLength": 300},
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 12,
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "maxLength": 500},
                            "tool": {"type": "string", "maxLength": 100},
                            "scope": {
                                "type": "string",
                                "maxLength": 500,
                                "description": (
                                    "Optional exact path, URL/domain, window title, repository "
                                    "root, or other value that limits this step."
                                ),
                            },
                        },
                        "required": ["action", "tool"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["title", "steps"],
            "additionalProperties": False,
        },
    ),
    _function(
        "desktop_list_windows",
        "List visible top-level Windows windows with exact handles, titles, PIDs, and rectangles.",
        {"type": "object", "properties": {}, "additionalProperties": False},
    ),
    _function(
        "desktop_window_action",
        (
            "Focus, minimise, maximise, restore, move, or resize one exact window returned by "
            "desktop_list_windows. Revalidates the handle and title before changing it."
        ),
        {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "focus",
                        "minimize",
                        "maximize",
                        "restore",
                        "move",
                        "resize",
                    ],
                },
                "window_handle": {"type": "integer", "minimum": 1},
                "window_title": {"type": "string"},
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "width": {"type": "integer", "minimum": 100, "maximum": 16384},
                "height": {"type": "integer", "minimum": 60, "maximum": 16384},
            },
            "required": ["action", "window_handle", "window_title"],
            "additionalProperties": False,
        },
    ),
    _function(
        "desktop_screenshot",
        "Capture the full virtual desktop or one exact visible window to a PNG file.",
        {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["full_screen", "window"]},
                "destination": {"type": "string"},
                "window_handle": {"type": "integer", "minimum": 1},
                "window_title": {"type": "string"},
            },
            "required": ["mode"],
            "additionalProperties": False,
        },
    ),
    _function(
        "desktop_ocr",
        "Extract text and text bounding boxes from one approved local image using bundled OCR.",
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    ),
    _function(
        "desktop_inspect_controls",
        (
            "Inspect visible UI Automation controls in the foreground window without clicking "
            "or activating them. Returns names, types, IDs, and screen rectangles."
        ),
        {
            "type": "object",
            "properties": {
                "max_controls": {"type": "integer", "minimum": 1, "maximum": 100}
            },
            "additionalProperties": False,
        },
    ),
    _function(
        "clipboard_read",
        "Read Unicode text from the Windows clipboard. Treat the raw clipboard as sensitive.",
        {"type": "object", "properties": {}, "additionalProperties": False},
    ),
    _function(
        "clipboard_write",
        "Replace the Windows Unicode-text clipboard with exact user-approved text.",
        {
            "type": "object",
            "properties": {"text": {"type": "string", "maxLength": 100000}},
            "required": ["text"],
            "additionalProperties": False,
        },
    ),
    _function(
        "desktop_mouse",
        "Perform one guarded generic mouse move, click, double-click, or wheel-scroll action.",
        {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["move", "click", "double_click", "scroll"],
                },
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "button": {"type": "string", "enum": ["left", "right", "middle"]},
                "amount": {"type": "integer", "minimum": -20, "maximum": 20},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    ),
    _function(
        "desktop_keyboard",
        "Type approved text or press a bounded keyboard combination of at most five keys.",
        {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["type", "press"]},
                "text": {"type": "string", "maxLength": 5000},
                "keys": {
                    "type": "array",
                    "maxItems": 5,
                    "items": {"type": "string", "maxLength": 20},
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    ),
]

TOOL_SCHEMAS = [*BASE_RUNTIME_TOOL_SCHEMAS, *ADDITIONAL_TOOL_SCHEMAS]
TOOL_NAMES = {schema["function"]["name"] for schema in TOOL_SCHEMAS}
DESKTOP_TOOL_NAMES = {
    "desktop_list_windows",
    "desktop_window_action",
    "desktop_screenshot",
    "desktop_ocr",
    "desktop_inspect_controls",
    "clipboard_read",
    "clipboard_write",
    "desktop_mouse",
    "desktop_keyboard",
}


def _is_structured_document(path: str) -> bool:
    return Path(path).suffix.casefold() in SUPPORTED_EXTENSIONS


def describe_tool(name: str, arguments: str) -> tuple[str, str, str | None]:
    """Describe a runtime tool for the host approval UI."""
    try:
        parsed = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        parsed = {}

    if name == "read_text_file" and _is_structured_document(str(parsed.get("path", ""))):
        return (
            f"Read structured document: {parsed.get('path', '')}",
            "Extract bounded document structure and content without editing the source file",
            (
                "Choose Y to keep document content terminal-only, or A to explicitly allow "
                "Groq access. Office package expansion and output are bounded before parsing."
            ),
        )
    if name not in DESKTOP_TOOL_NAMES and name != "propose_plan":
        return describe_base_tool(name, arguments)

    if name == "propose_plan":
        return ("Present a multi-step execution plan", "Request one-request scoped approval", None)
    if name == "desktop_list_windows":
        return (
            "List visible desktop windows",
            "Resolve exact window handles and geometry before manipulating the desktop",
            "Choose Y to keep window details terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "desktop_window_action":
        action = parsed.get("action", "unknown")
        window_label = (
            f"{str(action).upper()} window: {parsed.get('window_title', '')!r} "
            f"(handle {parsed.get('window_handle', '?')})"
        )
        return (
            window_label,
            "Manipulate the exact revalidated Windows window",
            (
                "Moving, resizing, minimizing, or focusing a window changes the visible "
                "desktop state."
            ),
        )
    if name == "desktop_screenshot":
        target = (
            "the full virtual desktop"
            if parsed.get("mode") == "full_screen"
            else f"window {parsed.get('window_title', '')!r}"
        )
        return (
            f"Capture {target} to {parsed.get('destination') or 'Interly captures folder'}",
            "Create an approved desktop PNG for visual inspection",
            "The screenshot may contain private information visible on screen.",
        )
    if name == "desktop_ocr":
        return (
            f"Run OCR on image: {parsed.get('path', '')}",
            "Extract visible text and its image coordinates",
            "Choose Y to keep OCR text terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "desktop_inspect_controls":
        return (
            "Inspect visible controls in the foreground window",
            "Identify UI elements and rectangles without activating them",
            "Choose Y to keep control details terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "clipboard_read":
        return (
            "Read Windows clipboard text",
            "Inspect the current clipboard without changing it",
            "Choose Y to keep clipboard text terminal-only, or A to explicitly allow Groq access.",
        )
    if name == "clipboard_write":
        text = str(parsed.get("text", ""))
        return (
            f"Replace Windows clipboard text ({len(text)} characters): {text[:300]!r}",
            "Put exact approved text on the clipboard",
            "This replaces the current text clipboard contents.",
        )
    if name == "desktop_mouse":
        return (
            (
                f"Mouse {parsed.get('action')} at "
                f"({parsed.get('x', 'current')}, {parsed.get('y', 'current')})"
            ),
            "Perform one generic pointer action on the visible desktop",
            "A click can activate whichever control is currently at the approved coordinates.",
        )
    if name == "desktop_keyboard":
        if parsed.get("action") == "type":
            text = str(parsed.get("text", ""))
            action = (
                f"Type {len(text)} characters into the currently focused desktop control: "
                f"{text[:300]!r}"
            )
        else:
            action = f"Press desktop key combination: {parsed.get('keys', [])}"
        return (
            action,
            "Perform one generic keyboard action in the currently focused desktop context",
            "Keyboard input goes to whichever control is focused when the action executes.",
        )
    return describe_base_tool(name, arguments)


def execute_tool(name: str, arguments: str = "{}") -> str | LocalOnlyResult:
    """Execute a runtime tool after host-side governance has approved it."""
    if name == "read_text_file":
        try:
            parsed = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return "Tool arguments were invalid JSON; nothing was executed."
        path = str(parsed.get("path", ""))
        if _is_structured_document(path):
            return LocalOnlyResult(
                (
                    "The approved structured document was read and its extracted content was "
                    "displayed only in the user's terminal. Do not infer its contents unless "
                    "the user explicitly allows Groq access."
                ),
                read_structured_document(path),
            )
        return execute_base_tool(name, arguments)

    if name not in DESKTOP_TOOL_NAMES:
        return execute_base_tool(name, arguments)
    try:
        parsed = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return "Tool arguments were invalid JSON; nothing was executed."

    if name == "desktop_list_windows":
        return LocalOnlyResult(
            "Visible desktop windows were listed only in the user's terminal.",
            list_windows(),
        )
    if name == "desktop_window_action":
        return window_action(
            str(parsed.get("action", "")),
            int(parsed.get("window_handle", 0)),
            str(parsed.get("window_title", "")),
            x=_optional_int(parsed.get("x")),
            y=_optional_int(parsed.get("y")),
            width=_optional_int(parsed.get("width")),
            height=_optional_int(parsed.get("height")),
        )
    if name == "desktop_screenshot":
        return capture_screen(
            str(parsed.get("mode", "")),
            str(parsed.get("destination", "")),
            window_handle=_optional_int(parsed.get("window_handle")),
            window_title=str(parsed.get("window_title", "")),
        )
    if name == "desktop_ocr":
        return LocalOnlyResult(
            "OCR completed and its text/coordinates were displayed only in the user's terminal.",
            ocr_image(str(parsed.get("path", ""))),
        )
    if name == "desktop_inspect_controls":
        return LocalOnlyResult(
            "Visible desktop controls were displayed only in the user's terminal.",
            inspect_visible_controls(int(parsed.get("max_controls", 100))),
        )
    if name == "clipboard_read":
        return LocalOnlyResult(
            "Clipboard text was displayed only in the user's terminal.",
            read_clipboard(),
        )
    if name == "clipboard_write":
        return write_clipboard(str(parsed.get("text", "")))
    if name == "desktop_mouse":
        return mouse_action(
            str(parsed.get("action", "")),
            x=_optional_int(parsed.get("x")),
            y=_optional_int(parsed.get("y")),
            button=str(parsed.get("button", "left")),
            amount=int(parsed.get("amount", 0)),
        )
    if name == "desktop_keyboard":
        return keyboard_action(
            str(parsed.get("action", "")),
            text=str(parsed.get("text", "")),
            keys=[str(item) for item in list(parsed.get("keys", []))],
        )
    return f"Unknown tool: {name}"


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
