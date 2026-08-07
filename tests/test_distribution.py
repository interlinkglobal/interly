import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[1]


def load_renderer() -> object:
    path = ROOT / "packaging" / "render_winget.py"
    spec = importlib.util.spec_from_file_location("render_winget", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_winget_renderer_creates_valid_release_manifests(tmp_path: Path) -> None:
    renderer = load_renderer()
    sha256 = "ab" * 32
    url = "https://github.com/interlinkglobal/Interly/releases/download/v0.6.0/InterlySetup-x64.exe"

    paths = renderer.render("0.6.0", url, sha256, tmp_path)

    assert len(paths) == 3
    installer = (tmp_path / "InterlinkGlobal.Interly.installer.yaml").read_text()
    assert "PackageIdentifier: InterlinkGlobal.Interly" in installer
    assert "PackageVersion: 0.6.0" in installer
    assert "InstallerType: inno" in installer
    assert "Commands:\n  - interly\n  - interlink" in installer
    assert "ReleaseDate: 2026-08-07" in installer
    assert f"InstallerUrl: {url}" in installer
    assert f"InstallerSha256: {sha256.upper()}" in installer


def test_distribution_files_keep_standalone_and_fallback_routes() -> None:
    workflow = (ROOT / ".github" / "workflows" / "windows-distribution.yml").read_text()
    readme = (ROOT / "README.md").read_text()

    assert "pyinstaller" in workflow.casefold()
    assert "Interly 0.6.0" in workflow
    assert "dist/interly.exe" in workflow
    assert "dist/interlink.exe" in workflow
    assert "InterlySetup-x64.exe" in workflow
    assert "Interly-0.6.0-winget-manifests.zip" in workflow
    assert "winget install --id InterlinkGlobal.Interly" in readme
    assert "install.ps1" in readme
