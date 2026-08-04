"""Render WinGet manifests after the Windows installer has been built."""

import argparse
from pathlib import Path

PACKAGE_ID = "InterlinkGlobal.Interly"
MANIFEST_VERSION = "1.12.0"


def render(version: str, installer_url: str, sha256: str, output: Path) -> list[Path]:
    """Write the three-file WinGet manifest for one Interly release."""
    output.mkdir(parents=True, exist_ok=True)
    normalized_hash = sha256.strip().upper()
    if len(normalized_hash) != 64 or any(c not in "0123456789ABCDEF" for c in normalized_hash):
        raise ValueError("Installer SHA-256 must contain exactly 64 hexadecimal characters.")

    files = {
        f"{PACKAGE_ID}.yaml": f"""PackageIdentifier: {PACKAGE_ID}
PackageVersion: {version}
DefaultLocale: en-US
ManifestType: version
ManifestVersion: {MANIFEST_VERSION}
""",
        f"{PACKAGE_ID}.locale.en-US.yaml": f"""PackageIdentifier: {PACKAGE_ID}
PackageVersion: {version}
PackageLocale: en-US
Publisher: Interlink Global Technologies
PublisherUrl: https://github.com/interlinkglobal
PublisherSupportUrl: https://github.com/interlinkglobal/Interly/issues
PackageName: Interly
PackageUrl: https://github.com/interlinkglobal/Interly
License: MIT
LicenseUrl: https://github.com/interlinkglobal/Interly/blob/main/LICENSE
ShortDescription: A permission-aware Windows computer agent powered by Groq.
Tags:
  - agent
  - automation
  - command-line
  - groq
  - windows
ManifestType: defaultLocale
ManifestVersion: {MANIFEST_VERSION}
""",
        f"{PACKAGE_ID}.installer.yaml": f"""PackageIdentifier: {PACKAGE_ID}
PackageVersion: {version}
InstallerType: inno
Scope: user
InstallModes:
  - interactive
  - silent
  - silentWithProgress
UpgradeBehavior: install
Commands:
  - interlink
ReleaseDate: 2026-08-04
Installers:
  - Architecture: x64
    InstallerUrl: {installer_url}
    InstallerSha256: {normalized_hash}
ManifestType: installer
ManifestVersion: {MANIFEST_VERSION}
""",
    }
    written = []
    for name, content in files.items():
        path = output / name
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--installer-url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.version, args.installer_url, args.sha256, args.output)


if __name__ == "__main__":
    main()
