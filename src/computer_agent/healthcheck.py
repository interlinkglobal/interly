"""Verify that the project's initial Python dependencies are available."""

from importlib.metadata import version

PACKAGES = (
    "beautifulsoup4",
    "groq",
    "pydantic-settings",
    "python-dotenv",
)


def main() -> None:
    """Print installed versions without making any network requests."""
    print("Computer agent environment is ready.")
    for package in PACKAGES:
        print(f"- {package}: {version(package)}")


if __name__ == "__main__":
    main()
