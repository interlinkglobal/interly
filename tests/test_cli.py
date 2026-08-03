from types import SimpleNamespace
from unittest.mock import patch

from computer_agent.__main__ import prompt_for_valid_groq_key


@patch("computer_agent.__main__.save_api_key")
@patch("computer_agent.__main__.Groq")
def test_blank_groq_key_is_never_validated_or_saved(groq: object, save: object) -> None:
    output: list[str] = []

    result = prompt_for_valid_groq_key(lambda _prompt: "", output.append)

    assert result is None
    groq.assert_not_called()
    save.assert_not_called()


@patch("computer_agent.__main__.save_api_key")
@patch("computer_agent.__main__.Groq")
def test_working_groq_key_is_validated_before_save(groq: object, save: object) -> None:
    groq.return_value.models.list.return_value = SimpleNamespace(data=[])
    save.return_value = SimpleNamespace(parent="config-directory")

    result = prompt_for_valid_groq_key(lambda _prompt: "new-key", lambda _text: None)

    assert result == "new-key"
    groq.return_value.models.list.assert_called_once_with()
    save.assert_called_once_with("new-key")
