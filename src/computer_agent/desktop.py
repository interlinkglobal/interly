"""Guarded Windows desktop perception and interaction primitives."""

from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from computer_agent.config import desktop_capture_dir

MAX_CONTROLS = 100
MAX_OCR_LINES = 500
MAX_CLIPBOARD_CHARS = 100_000
MAX_TYPED_CHARS = 5_000


def _require_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("Desktop tools are available only on Windows.")


def _user32() -> Any:
    _require_windows()
    return ctypes.windll.user32


def _kernel32() -> Any:
    _require_windows()
    return ctypes.windll.kernel32


def list_windows() -> str:
    """List visible top-level Windows windows with stable native handles."""
    user32 = _user32()
    windows: list[dict[str, Any]] = []
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return True
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        windows.append(
            {
                "window_handle": int(hwnd),
                "title": title,
                "process_id": int(pid.value),
                "left": int(rect.left),
                "top": int(rect.top),
                "width": int(rect.right - rect.left),
                "height": int(rect.bottom - rect.top),
            }
        )
        return len(windows) < 100

    user32.EnumWindows(enum_proc(callback), 0)
    windows.sort(key=lambda item: (item["title"].casefold(), item["window_handle"]))
    return json.dumps(windows, indent=2, ensure_ascii=False)


def window_action(
    action: str,
    window_handle: int,
    window_title: str,
    *,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> str:
    """Manipulate one exact current top-level window after revalidating its title."""
    user32 = _user32()
    hwnd = int(window_handle)
    current = _window_details(hwnd)
    if current is None or current["title"] != window_title:
        return "Window handle and title no longer match a visible window; nothing changed."

    show_codes = {"minimize": 6, "maximize": 3, "restore": 9}
    if action in show_codes:
        user32.ShowWindow(hwnd, show_codes[action])
        return f"Window {action} requested for {window_title!r}."
    if action == "focus":
        user32.ShowWindow(hwnd, 9)
        if not user32.SetForegroundWindow(hwnd):
            return "Windows refused to move this window to the foreground."
        return f"Focused window {window_title!r}."
    if action not in {"move", "resize"}:
        return f"Unknown window action: {action}"

    left = current["left"] if x is None else int(x)
    top = current["top"] if y is None else int(y)
    new_width = current["width"] if width is None else int(width)
    new_height = current["height"] if height is None else int(height)
    if action == "move" and (x is None or y is None):
        return "Move requires both x and y coordinates."
    if action == "resize" and (width is None or height is None):
        return "Resize requires both width and height."
    if new_width < 100 or new_height < 60 or new_width > 16_384 or new_height > 16_384:
        return "Requested window size is outside Interly's allowed bounds."

    flags = 0x0004 | 0x0010
    if not user32.SetWindowPos(hwnd, 0, left, top, new_width, new_height, flags):
        return "Windows rejected the requested window position or size."
    return (
        f"Updated window {window_title!r}: left={left}, top={top}, "
        f"width={new_width}, height={new_height}."
    )


def capture_screen(
    mode: str,
    destination: str = "",
    *,
    window_handle: int | None = None,
    window_title: str = "",
) -> str:
    """Capture the virtual desktop or one exact visible window to a PNG file."""
    _require_windows()
    from PIL import ImageGrab

    path = _capture_path(destination, mode)
    if path.exists():
        return f"Destination already exists; screenshot was not written: {path}"
    path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "full_screen":
        image = ImageGrab.grab(all_screens=True)
    elif mode == "window":
        if window_handle is None or not window_title:
            return "Window screenshot requires an exact window handle and title."
        details = _window_details(int(window_handle))
        if details is None or details["title"] != window_title:
            return "Window handle and title no longer match a visible window; nothing captured."
        bbox = (
            details["left"],
            details["top"],
            details["left"] + details["width"],
            details["top"] + details["height"],
        )
        image = ImageGrab.grab(bbox=bbox, all_screens=True)
    else:
        return f"Unknown screenshot mode: {mode}"

    image.save(path, format="PNG")
    return json.dumps(
        {
            "path": str(path),
            "mode": mode,
            "width": image.width,
            "height": image.height,
        },
        indent=2,
    )


def ocr_image(path: str) -> str:
    """Extract text and bounding boxes from one approved local image using bundled OCR."""
    _require_windows()
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        return f"Image does not exist: {source}"
    if source.stat().st_size > 50_000_000:
        return "OCR image exceeds the 50 MB limit."
    supported = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
    if source.suffix.casefold() not in supported:
        return "OCR supports PNG, JPEG, BMP, WebP, and TIFF images."

    from rapidocr import RapidOCR

    result = RapidOCR()(str(source))
    txts = list(result.txts or [])[:MAX_OCR_LINES]
    scores = list(result.scores or [])[:MAX_OCR_LINES]
    boxes = result.boxes
    box_rows = boxes.tolist()[:MAX_OCR_LINES] if boxes is not None else []
    lines: list[dict[str, Any]] = []
    for index, text in enumerate(txts):
        score = float(scores[index]) if index < len(scores) else None
        box = box_rows[index] if index < len(box_rows) else None
        lines.append({"text": str(text), "score": score, "box": box})
    payload = {
        "path": str(source),
        "text": "\n".join(str(item) for item in txts),
        "lines": lines,
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    if len(rendered) > 60_000:
        rendered = rendered[:60_000] + "\n[OCR output truncated by Interly]"
    return rendered


def inspect_visible_controls(max_controls: int = MAX_CONTROLS) -> str:
    """Inspect the foreground window's visible UI Automation controls without activating them."""
    _require_windows()
    import uiautomation as auto

    limit = max(1, min(int(max_controls), MAX_CONTROLS))
    auto.SetGlobalSearchTimeout(1)
    foreground = auto.GetForegroundControl()
    if foreground is None:
        return "No foreground UI Automation control was available."

    controls: list[dict[str, Any]] = []
    queue: list[tuple[Any, int]] = [(foreground, 0)]
    while queue and len(controls) < limit:
        control, depth = queue.pop(0)
        try:
            name = str(getattr(control, "Name", "") or "")
            control_type = str(getattr(control, "ControlTypeName", "") or "")
            automation_id = str(getattr(control, "AutomationId", "") or "")
            offscreen = bool(getattr(control, "IsOffscreen", False))
            rect = getattr(control, "BoundingRectangle", None)
            bounds = _uia_rect(rect)
        except (LookupError, OSError, RuntimeError):
            continue
        if not offscreen and bounds and (name or automation_id or control_type):
            controls.append(
                {
                    "control_id": len(controls),
                    "name": name or None,
                    "type": control_type or None,
                    "automation_id": automation_id or None,
                    "rectangle": bounds,
                }
            )
        if depth >= 5:
            continue
        try:
            children = list(control.GetChildren())
        except (LookupError, OSError, RuntimeError):
            children = []
        for child in children[:50]:
            queue.append((child, depth + 1))
    return json.dumps(controls, indent=2, ensure_ascii=False)


def read_clipboard() -> str:
    """Read Unicode text from the Windows clipboard."""
    user32 = _user32()
    kernel32 = _kernel32()
    cf_unicode_text = 13
    kernel32.GlobalLock.restype = ctypes.c_void_p
    user32.GetClipboardData.restype = ctypes.c_void_p
    if not user32.OpenClipboard(None):
        return "Clipboard is currently unavailable."
    try:
        handle = user32.GetClipboardData(cf_unicode_text)
        if not handle:
            return "Clipboard does not currently contain Unicode text."
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return "Clipboard text could not be locked for reading."
        try:
            text = ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()
    if len(text) > MAX_CLIPBOARD_CHARS:
        return text[:MAX_CLIPBOARD_CHARS] + "\n[Clipboard text truncated by Interly]"
    return text


def write_clipboard(text: str) -> str:
    """Replace the Windows Unicode-text clipboard with exact approved text."""
    if len(text) > MAX_CLIPBOARD_CHARS:
        return f"Clipboard text exceeds the {MAX_CLIPBOARD_CHARS:,}-character limit."
    user32 = _user32()
    kernel32 = _kernel32()
    cf_unicode_text = 13
    gmem_moveable = 0x0002
    data = (text + "\0").encode("utf-16-le")
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.restype = ctypes.c_void_p
    user32.SetClipboardData.restype = ctypes.c_void_p
    handle = kernel32.GlobalAlloc(gmem_moveable, len(data))
    if not handle:
        return "Could not allocate clipboard memory."
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        return "Could not lock clipboard memory."
    ctypes.memmove(pointer, data, len(data))
    kernel32.GlobalUnlock(handle)
    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        return "Clipboard is currently unavailable."
    success = False
    try:
        user32.EmptyClipboard()
        success = bool(user32.SetClipboardData(cf_unicode_text, handle))
    finally:
        user32.CloseClipboard()
    if not success:
        kernel32.GlobalFree(handle)
        return "Windows rejected the clipboard write."
    return f"Clipboard text replaced ({len(text)} characters)."


def mouse_action(
    action: str,
    *,
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
    amount: int = 0,
) -> str:
    """Perform one bounded generic mouse action through pynput."""
    _require_windows()
    from pynput.mouse import Button, Controller

    controller = Controller()
    if action in {"move", "click", "double_click"}:
        if x is None or y is None:
            return f"Mouse {action} requires x and y coordinates."
        if not _point_on_virtual_desktop(int(x), int(y)):
            return "Mouse coordinates are outside the virtual desktop bounds."
        controller.position = (int(x), int(y))
    buttons = {"left": Button.left, "right": Button.right, "middle": Button.middle}
    if button not in buttons:
        return f"Unknown mouse button: {button}"
    if action == "move":
        return f"Moved pointer to ({int(x)}, {int(y)})."
    if action == "click":
        controller.click(buttons[button], 1)
        return f"Clicked {button} at ({int(x)}, {int(y)})."
    if action == "double_click":
        controller.click(buttons[button], 2)
        return f"Double-clicked {button} at ({int(x)}, {int(y)})."
    if action == "scroll":
        bounded = max(-20, min(20, int(amount)))
        if bounded == 0:
            return "Scroll amount must be between -20 and 20 and cannot be zero."
        controller.scroll(0, bounded)
        return f"Scrolled mouse wheel by {bounded}."
    return f"Unknown mouse action: {action}"


def keyboard_action(action: str, *, text: str = "", keys: list[str] | None = None) -> str:
    """Perform one bounded generic keyboard action through pynput."""
    _require_windows()
    from pynput.keyboard import Controller, Key

    controller = Controller()
    if action == "type":
        if len(text) > MAX_TYPED_CHARS:
            return f"Typed text exceeds the {MAX_TYPED_CHARS:,}-character limit."
        controller.write(text)
        return f"Typed {len(text)} characters."
    if action != "press":
        return f"Unknown keyboard action: {action}"
    raw_keys = keys or []
    if not raw_keys or len(raw_keys) > 5:
        return "Keyboard press requires between 1 and 5 keys."
    resolved = [_resolve_key(Key, item) for item in raw_keys]
    if any(item is None for item in resolved):
        bad = [raw for raw, resolved_key in zip(raw_keys, resolved) if resolved_key is None]
        return f"Unsupported key name(s): {', '.join(bad)}"
    for item in resolved:
        controller.press(item)
    for item in reversed(resolved):
        controller.release(item)
    return f"Pressed key combination: {' + '.join(raw_keys)}."


def _resolve_key(key_type: Any, name: str) -> Any | None:
    normal = name.casefold().replace("-", "_")
    aliases = {
        "ctrl": "ctrl",
        "control": "ctrl",
        "win": "cmd",
        "windows": "cmd",
        "escape": "esc",
    }
    normal = aliases.get(normal, normal)
    if len(name) == 1:
        return name
    allowed = {
        "alt",
        "alt_l",
        "alt_r",
        "backspace",
        "caps_lock",
        "cmd",
        "ctrl",
        "ctrl_l",
        "ctrl_r",
        "delete",
        "down",
        "end",
        "enter",
        "esc",
        "home",
        "insert",
        "left",
        "page_down",
        "page_up",
        "right",
        "shift",
        "shift_l",
        "shift_r",
        "space",
        "tab",
        "up",
        "f1",
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
        "f7",
        "f8",
        "f9",
        "f10",
        "f11",
        "f12",
    }
    return getattr(key_type, normal, None) if normal in allowed else None


def _capture_path(destination: str, mode: str) -> Path:
    if destination:
        path = Path(destination).expanduser().resolve()
        if path.suffix.casefold() != ".png":
            raise ValueError("Desktop screenshots must use a .png destination.")
        return path
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    return desktop_capture_dir() / f"{mode}-{timestamp}.png"


def _window_details(hwnd: int) -> dict[str, Any] | None:
    user32 = _user32()
    if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
        return None
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(max(1, length + 1))
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    title = buffer.value.strip()
    if not title:
        return None
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return {
        "title": title,
        "left": int(rect.left),
        "top": int(rect.top),
        "width": int(rect.right - rect.left),
        "height": int(rect.bottom - rect.top),
    }


def _point_on_virtual_desktop(x: int, y: int) -> bool:
    user32 = _user32()
    left = int(user32.GetSystemMetrics(76))
    top = int(user32.GetSystemMetrics(77))
    width = int(user32.GetSystemMetrics(78))
    height = int(user32.GetSystemMetrics(79))
    return left <= x < left + width and top <= y < top + height


def _uia_rect(rect: Any) -> dict[str, int] | None:
    if rect is None:
        return None
    left = getattr(rect, "left", getattr(rect, "Left", None))
    top = getattr(rect, "top", getattr(rect, "Top", None))
    right = getattr(rect, "right", getattr(rect, "Right", None))
    bottom = getattr(rect, "bottom", getattr(rect, "Bottom", None))
    if None in {left, top, right, bottom}:
        return None
    width = int(right - left)
    height = int(bottom - top)
    if width <= 0 or height <= 0:
        return None
    return {"left": int(left), "top": int(top), "width": width, "height": height}
