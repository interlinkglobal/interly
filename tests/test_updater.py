import json
from types import SimpleNamespace
from unittest.mock import patch

from computer_agent.updater import installed_commit, update_interly, update_standalone


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
