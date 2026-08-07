"""Self-update support for standalone and pipx installations."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

import httpx

from computer_agent import __version__

PACKAGE_NAME = "interly"
WINGET_PACKAGE_ID = "InterlinkGlobal.Interly"
UPDATE_BRANCH = "main"
UPDATE_REF_URL = (
    "https://api.github.com/repos/interlinkglobal/Interly/git/ref/heads/"
    f"{UPDATE_BRANCH}"
)
LATEST_RELEASE_URL = "https://api.github.com/repos/interlinkglobal/Interly/releases/latest"
INSTALLER_NAME = "InterlySetup-x64.exe"
MAX_INSTALLER_BYTES = 200 * 1024 * 1024


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
    """Return the current commit at Interly's update branch."""
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
    """Upgrade through WinGet when frozen, otherwise update the pipx installation."""
    if getattr(sys, "frozen", False):
        return update_standalone()

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
        "Type exit, then run interly again to use the new version."
    )


def update_standalone() -> str:
    """Try WinGet, then use a verified GitHub Release installer as fallback."""
    winget = shutil.which("winget")
    if winget:
        try:
            completed = subprocess.run(
                [
                    winget,
                    "upgrade",
                    "--id",
                    WINGET_PACKAGE_ID,
                    "--exact",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                    "--disable-interactivity",
                ],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=300,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            completed = None
        if completed is not None and completed.returncode == 0:
            output = (completed.stdout or completed.stderr).strip()
            return (
                f"WinGet finished checking Interly.\n{output}\n"
                "Type exit, then run interly again to use an installed update."
            )

    try:
        version, installer_url, expected_digest = latest_release_installer()
        if version == __version__:
            return f"Interly is already current ({version})."
        installer = download_release_installer(installer_url, expected_digest)
        subprocess.Popen(
            [str(installer), "/SILENT", "/NORESTART", "/CLOSEAPPLICATIONS"],
            close_fds=True,
        )
    except (httpx.HTTPError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        return f"Update failed safely; the current installation was kept: {error}"
    return (
        f"Interly {version} was downloaded, verified, and its installer was started. "
        "Finish the installer, type exit, then run interly again."
    )


def latest_release_installer() -> tuple[str, str, str]:
    """Return the latest release version, installer URL, and GitHub SHA-256 digest."""
    response = httpx.get(
        LATEST_RELEASE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Interly updater"},
        timeout=15.0,
    )
    response.raise_for_status()
    release = response.json()
    version = str(release.get("tag_name", "")).removeprefix("v")
    if not version:
        raise RuntimeError("GitHub returned no release version.")
    asset = next(
        (item for item in release.get("assets", []) if item.get("name") == INSTALLER_NAME),
        None,
    )
    if not asset:
        raise RuntimeError("The latest release has no Windows installer.")
    url = str(asset.get("browser_download_url", ""))
    digest = str(asset.get("digest", ""))
    expected_prefix = "https://github.com/interlinkglobal/Interly/releases/download/"
    if not url.startswith(expected_prefix) or not digest.startswith("sha256:"):
        raise RuntimeError("The release installer could not be verified.")
    return version, url, digest.removeprefix("sha256:").casefold()


def download_release_installer(url: str, expected_digest: str) -> Path:
    """Download a bounded installer to a temporary file and verify its SHA-256 digest."""
    destination = Path(tempfile.gettempdir()) / "InterlySetup-update-x64.exe"
    temporary = destination.with_suffix(".download")
    digest = hashlib.sha256()
    size = 0
    try:
        with temporary.open("wb") as output, httpx.stream(
            "GET",
            url,
            headers={"User-Agent": "Interly updater"},
            follow_redirects=True,
            timeout=60.0,
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_INSTALLER_BYTES:
                    raise RuntimeError("The release installer exceeded the size limit.")
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != expected_digest:
            raise RuntimeError("The release installer failed SHA-256 verification.")
        temporary.replace(destination)
        return destination
    except (httpx.HTTPError, OSError, RuntimeError):
        temporary.unlink(missing_ok=True)
        raise


def digest_file(path: Path) -> str:
    """Return a file's lowercase SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
