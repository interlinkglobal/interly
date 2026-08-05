"""Permission-gated file operations with bounded reads and explicit paths."""

import difflib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

MAX_FILE_BYTES = 1_000_000
MAX_RESULTS = 100


def _path(value: str) -> Path:
    if not value.strip():
        raise ValueError("A path is required.")
    return Path(value).expanduser().resolve()


def search_files(
    root: str,
    query: str,
    extension: str = "",
    content: str = "",
    modified_after: str = "",
    modified_before: str = "",
) -> str:
    base = _path(root)
    if not base.is_dir():
        return f"Search root is not a directory: {base}"
    needle = query.casefold()
    suffix = extension.casefold().lstrip(".")
    try:
        after = datetime.fromisoformat(modified_after) if modified_after else None
        before = datetime.fromisoformat(modified_before) if modified_before else None
        after = after.astimezone(UTC) if after else None
        before = before.astimezone(UTC) if before else None
    except ValueError:
        return "Invalid modified date; use an ISO date such as 2026-08-03."
    matches: list[dict[str, object]] = []
    for candidate in base.rglob("*"):
        if len(matches) >= MAX_RESULTS:
            break
        try:
            if not candidate.is_file() or (needle and needle not in candidate.name.casefold()):
                continue
            if suffix and candidate.suffix.casefold().lstrip(".") != suffix:
                continue
            stat = candidate.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, UTC)
            if after and modified < after:
                continue
            if before and modified > before:
                continue
            if content:
                if candidate.stat().st_size > MAX_FILE_BYTES:
                    continue
                if content.casefold() not in candidate.read_text(errors="replace").casefold():
                    continue
            matches.append(
                {
                    "path": str(candidate),
                    "bytes": stat.st_size,
                    "modified": modified.isoformat(timespec="seconds"),
                }
            )
        except (OSError, UnicodeError):
            continue
    return json.dumps(matches, indent=2) if matches else "No matching files found."


def read_text_file(path: str) -> str:
    target = _path(path)
    if not target.is_file():
        return f"File does not exist: {target}"
    size = target.stat().st_size
    if size > MAX_FILE_BYTES:
        return f"File is too large to read ({size} bytes; limit {MAX_FILE_BYTES})."
    return f"Path: {target}\n\n{target.read_text(errors='replace')}"


def create_text_file(path: str, content: str) -> str:
    target = _path(path)
    if target.exists():
        return f"Destination already exists; nothing was overwritten: {target}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Created {target} ({len(content.encode('utf-8'))} bytes)."


def edit_text_file(path: str, old_text: str, new_text: str) -> str:
    target = _path(path)
    if not target.is_file():
        return f"File does not exist: {target}"
    original = target.read_text(errors="replace")
    count = original.count(old_text)
    if not old_text or count != 1:
        return f"Expected exactly one matching passage, found {count}; nothing was changed."
    target.write_text(original.replace(old_text, new_text, 1), encoding="utf-8")
    return f"Updated one exact passage in {target}."


def compare_files(left: str, right: str) -> str:
    left_path, right_path = _path(left), _path(right)
    left_lines = left_path.read_text(errors="replace").splitlines()
    right_lines = right_path.read_text(errors="replace").splitlines()
    diff = "\n".join(difflib.unified_diff(left_lines, right_lines, fromfile=str(left_path), tofile=str(right_path), lineterm=""))
    return diff[:50_000] or "The files have identical text content."


def manage_path(action: str, source: str, destination: str) -> str:
    destination_path = _path(destination)
    if action == "mkdir":
        if destination_path.exists():
            return f"Destination already exists: {destination_path}"
        destination_path.mkdir(parents=True)
        return f"Created directory {destination_path}."
    source_path = _path(source)
    if not source_path.exists():
        return f"Source does not exist: {source_path}"
    if destination_path.exists():
        return f"Destination already exists; nothing was overwritten: {destination_path}"
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if action == "copy":
        shutil.copytree(source_path, destination_path) if source_path.is_dir() else shutil.copy2(source_path, destination_path)
    elif action in {"move", "rename"}:
        shutil.move(str(source_path), str(destination_path))
    else:
        return f"Unknown file action: {action}"
    verb = "Copied" if action == "copy" else "Moved" if action == "move" else "Renamed"
    return f"{verb} {source_path} to {destination_path}."
