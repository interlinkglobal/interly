from pathlib import Path
from unittest.mock import patch

from computer_agent.config import config_file, load_settings, save_api_key


def test_config_path_uses_portable_user_directory(monkeypatch) -> None:
    monkeypatch.setenv("INTERLY_CONFIG_DIR", r"C:\Portable\Interly")

    assert config_file() == Path(r"C:\Portable\Interly\.env")


def test_environment_api_key_is_supported(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    assert load_settings().groq_api_key == "test-key"


@patch("computer_agent.config.Path.write_text")
@patch("computer_agent.config.Path.mkdir")
def test_save_api_key_creates_user_config_directory(mkdir: object, write_text: object) -> None:
    path = save_api_key("test-key")

    mkdir.assert_called_once_with(parents=True, exist_ok=True)
    write_text.assert_called_once_with("GROQ_API_KEY=test-key\n", encoding="utf-8")
    assert path.name == ".env"
