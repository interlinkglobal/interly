from pathlib import Path

INSTALLER = Path(__file__).parents[1] / "install.ps1"


def test_windows_installer_bootstraps_required_components() -> None:
    script = INSTALLER.read_text(encoding="utf-8")

    assert "Python.Python.3.13" in script
    assert "www.python.org/ftp/python/" in script
    assert "Git.Git" in script
    assert "git-for-windows/git/releases/latest" in script
    assert "-m pip install --user --upgrade pipx" in script
    assert "-m pipx ensurepath" in script
    assert "-m pipx install --force $InterlySpec" in script
    assert "Interly.git@main" in script
    assert "agent/next-ten-roadmap" not in script
    assert "& $interlyPath" in script


def test_readme_exposes_one_cmd_compatible_install_command() -> None:
    readme = (INSTALLER.parent / "README.md").read_text(encoding="utf-8")

    assert "powershell -NoProfile -ExecutionPolicy Bypass" in readme
    assert "Interly/main/install.ps1' | iex" in readme
    assert "Node.js" in readme
    assert "not required" in readme
