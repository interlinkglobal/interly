"""Lightweight repository-oriented workflows for developer-agent support."""

import json
import subprocess
from pathlib import Path
from typing import Any


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
