"""Lightweight repository-oriented workflows for developer-agent support."""

import json
import subprocess
from pathlib import Path
from typing import Any


class WorkflowRegistry:
    """Persist reusable named workflows on disk."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else Path.home() / ".config" / "Interly" / "workflows.json"
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

    def save_workflow(self, name: str, definition: dict[str, Any]) -> dict[str, Any]:
        entries = self._read()
        new_entry = {"name": name, "definition": definition}
        for index, entry in enumerate(entries):
            if entry.get("name") == name:
                entries[index] = new_entry
                self._write(entries)
                return new_entry
        entries.append(new_entry)
        self._write(entries)
        return new_entry

    def list_workflows(self) -> list[dict[str, Any]]:
        return self._read()


class RepositoryWorkflow:
    """Inspect a repository and run bounded commands safely."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def inspect(self) -> dict[str, Any]:
        files: list[dict[str, Any]] = []
        for path in sorted(self.root.rglob("*")):
            if path.is_file() and not any(part in {".git", "__pycache__"} for part in path.parts):
                files.append({"name": path.name, "path": str(path.relative_to(self.root))})
        return {"root": str(self.root), "files": files}

    def run_command(self, command: list[str], timeout: int = 30) -> dict[str, Any]:
        completed = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def run_named_workflow(self, command: list[str], timeout: int = 30) -> dict[str, Any]:
        return self.run_command(command, timeout=timeout)
