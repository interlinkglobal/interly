import hashlib
import json
from types import SimpleNamespace
from unittest.mock import patch

from computer_agent.updater import (
    MAX_INSTALLER_BYTES,
    UPDATE_BRANCH,
    digest_file,
    installed_commit,
    latest_release_installer,
    update_interly,
    update_standalone,
)


def test_pipx_update_branch_is_main() -> None:
    assert UPDATE_BRANCH == "main"


def test_installer_size_limit_allows_current_windows_bundle() -> None:
    assert MAX_INSTALLER_BYTES >= 400 * 1024 * 1024


@patch("computer_agent.updater.distribution")
def test_installed_commit_reads_pip_vcs_metadata(metadata: object) -> None:
    metadata.return_value.read_text.return_value = json.dumps(
        {"vcs_info": {"commit_id": "abc123"}}
    )

    assert installed_commit() == "abc123"


@patch("computer_agent.updater.repository_commit", return_value="same-commit")
@patch("computer_agent.updater.installed_commit", return_value="same-commit")
@patch("computer_agent.updater.subprocess.run")
def test_current_installation_does_not_run_pipx(
    run: object, _installed: object, _repository: object
) -> None:
    result = update_interly()

    assert "already current" in result
    run.assert_not_called()


@patch("computer_agent.updater.shutil.which", return_value="C:/Python/Scripts/pipx.exe")
@patch("computer_agent.updater.repository_commit", return_value="new-commit")
@patch("computer_agent.updater.installed_commit", return_value="old-commit")
@patch("computer_agent.updater.subprocess.run")
def test_new_commit_upgrades_existing_pipx_installation(
    run: object, _installed: object, _repository: object, _which: object
) -> None:
    run.return_value = SimpleNamespace(returncode=0, stdout="upgraded", stderr="")

    result = update_interly()

    assert "updated from" in result
    assert "run interly again" in result
    run.assert_called_once_with(
        ["C:/Python/Scripts/pipx.exe", "upgrade", "interly"],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
        check=False,
    )


@patch("computer_agent.updater.shutil.which", return_value="C:/Windows/winget.exe")
@patch("computer_agent.updater.subprocess.run")
def test_standalone_update_uses_winget(run: object, _which: object) -> None:
    run.return_value = SimpleNamespace(returncode=0, stdout="No update available", stderr="")

    result = update_standalone()

    assert "WinGet finished" in result
    run.assert_called_once_with(
        [
            "C:/Windows/winget.exe",
            "upgrade",
            "--id",
            "InterlinkGlobal.Interly",
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


@patch("computer_agent.updater.subprocess.Popen")
@patch("computer_agent.updater.download_release_installer")
@patch("computer_agent.updater.latest_release_installer")
@patch("computer_agent.updater.shutil.which", return_value="C:/Windows/winget.exe")
@patch("computer_agent.updater.subprocess.run")
def test_standalone_falls_back_to_verified_release_when_winget_cannot_find_package(
    run: object,
    _which: object,
    release: object,
    download: object,
    popen: object,
) -> None:
    run.return_value = SimpleNamespace(returncode=1, stdout="", stderr="No package found")
    release.return_value = (
        "0.6.1",
        "https://github.com/interlinkglobal/interly/releases/download/v0.6.1/InterlySetup-x64.exe",
        "ab" * 32,
    )
    download.return_value = "C:/Temp/InterlySetup-update-x64.exe"

    result = update_standalone()

    assert "downloaded, verified" in result
    assert "run interly again" in result
    download.assert_called_once()
    popen.assert_called_once_with(
        [
            "C:/Temp/InterlySetup-update-x64.exe",
            "/SILENT",
            "/NORESTART",
            "/CLOSEAPPLICATIONS",
        ],
        close_fds=True,
    )


@patch("computer_agent.updater.httpx.get")
def test_latest_release_requires_official_installer_and_sha256(get: object) -> None:
    get.return_value.json.return_value = {
        "tag_name": "0.6.0",
        "assets": [
            {
                "name": "InterlySetup-x64.exe",
                "browser_download_url": (
                    "https://github.com/interlinkglobal/interly/releases/download/"
                    "0.6.0/InterlySetup-x64.exe"
                ),
                "digest": f"sha256:{'ab' * 32}",
            }
        ],
    }

    assert latest_release_installer() == (
        "0.6.0",
        "https://github.com/interlinkglobal/interly/releases/download/0.6.0/InterlySetup-x64.exe",
        "ab" * 32,
    )


def test_digest_file_returns_sha256(tmp_path: object) -> None:
    path = tmp_path / "installer.exe"
    path.write_bytes(b"verified installer")

    assert digest_file(path) == hashlib.sha256(b"verified installer").hexdigest()
