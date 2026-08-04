"""Repository-aware self-update support for pipx installations."""

import json
import shutil
import subprocess
from importlib.metadata import PackageNotFoundError, distribution

import httpx

PACKAGE_NAME = "interly"
UPDATE_BRANCH = "agent/next-ten-roadmap"
UPDATE_REF_URL = (
    "https://api.github.com/repos/interlinkglobal/Interly/git/ref/heads/"
    f"{UPDATE_BRANCH}"
)


def installed_commit() -> str | None:
    """Read the immutable VCS commit recorded by pip for this installation."""
    try:
        direct_url = distribution(PACKAGE_NAME).read_text("direct_url.json")
    except PackageNotFoundError:
        return None
    if not direct_url:
        return None
    try:
        data = json.loads(direct_url)
    except json.JSONDecodeError:
        return None
    commit = data.get("vcs_info", {}).get("commit_id")
    return str(commit) if commit else None


def repository_commit() -> str:
    """Return the current commit at Interly's development update branch."""
    response = httpx.get(
        UPDATE_REF_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Interly updater"},
        timeout=15.0,
    )
    response.raise_for_status()
    commit = response.json().get("object", {}).get("sha")
    if not commit:
        raise RuntimeError("GitHub returned no branch commit.")
    return str(commit)


def update_interly() -> str:
    """Check the repository and upgrade the pipx installation when needed."""
    try:
        current = installed_commit()
        latest = repository_commit()
    except (httpx.HTTPError, OSError, RuntimeError) as error:
        return f"Update check failed safely: {error}"

    if current == latest:
        return f"Interly is already current ({latest[:8]})."

    pipx = shutil.which("pipx")
    if not pipx:
        return "Update unavailable: pipx was not found on PATH. Nothing was changed."

    try:
        completed = subprocess.run(
            [pipx, "upgrade", PACKAGE_NAME],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"Update failed safely: {error}"

    output = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        return f"Update failed; the current installation was kept.\n{output}"
    previous = current[:8] if current else "unknown"
    return (
        f"Interly updated from {previous} to {latest[:8]}.\n"
        "Type exit, then run interlink again to use the new version."
    )
