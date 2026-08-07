"""Persistent memory storage for approved Interly facts and preferences."""

import json
from pathlib import Path
from typing import Any

from computer_agent.config import memory_file


class MemoryStore:
    """Store and retrieve approved memory entries on disk."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else memory_file()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        if isinstance(raw, list):
            return [entry for entry in raw if isinstance(entry, dict)]
        return []

    def _write(self, entries: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def add_entry(self, key: str, value: Any, *, kind: str = "fact", approved: bool = True) -> dict[str, Any]:
        if not approved:
            raise ValueError("Only approved entries can be stored in memory.")
        entries = self._read()
        updated = False
        new_entry = {
            "key": key,
            "value": value,
            "kind": kind,
            "approved": approved,
        }
        for index, entry in enumerate(entries):
            if entry.get("key") == key:
                entries[index] = new_entry
                updated = True
                break
        if not updated:
            entries.append(new_entry)
        self._write(entries)
        return new_entry

    def list_entries(self) -> list[dict[str, Any]]:
        return self._read()

    def delete_entry(self, key: str) -> bool:
        entries = self._read()
        remaining = [entry for entry in entries if entry.get("key") != key]
        if len(remaining) == len(entries):
            return False
        self._write(remaining)
        return True
