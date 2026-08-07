from types import SimpleNamespace
from unittest.mock import patch

from computer_agent.chat import run_chat
from computer_agent.models import GroqModel, ModelTurn, OfflineModel, ToolRequest
from computer_agent.tools import LocalOnlyResult


def test_offline_model_can_see_conversation_history() -> None:
    model = OfflineModel()
    messages = [
        {"role": "user", "content": "First"},
        {"role": "assistant", "content": "Reply"},
        {"role": "user", "content": "Second"},
    ]

    reply = model.reply(messages).content

    assert reply is not None
    assert 'I received: "Second"' in reply
    assert "2 user message(s)" in reply


def test_chat_ignores_empty_input_and_stops_on_exit() -> None:
    answers = iter(["", "Hello", "exit"])
    output: list[str] = []

    history = run_chat(
        model=OfflineModel(),
        read_input=lambda _prompt: next(answers),
        write_output=output.append,
    )

    assert [message["role"] for message in history] == ["user", "assistant"]
    assert history[0]["content"] == "Hello"
    assert output[-1] == "Goodbye!"


def test_update_command_bypasses_model_and_runs_updater() -> None:
    answers = iter(["update", "exit"])
    output: list[str] = []
    model = OfflineModel()

    history = run_chat(
        model=model,
        read_input=lambda _prompt: next(answers),
        write_output=output.append,
        update_interly=lambda: "Interly is already current.",
    )

    assert history == []
    assert "Checking the Interly repository for updates..." in output
    assert "Interly is already current." in output


def test_memory_command_lists_stored_entries(tmp_path, monkeypatch) -> None:
    from computer_agent.memory import MemoryStore

    monkeypatch.setenv("INTERLY_CONFIG_DIR", str(tmp_path))
    store = MemoryStore(tmp_path / "memory.json")
    store.add_entry("name", "Ada", approved=True)

    output: list[str] = []
    answers = iter(["memory", "exit"])

    run_chat(
        model=OfflineModel(),
        read_input=lambda _prompt: next(answers),
        write_output=output.append,
    )

    assert "Stored memory:" in output
    assert "- name: Ada" in output


def test_memory_add_command_stores_entry(tmp_path, monkeypatch) -> None:
    from computer_agent.memory import MemoryStore

    monkeypatch.setenv("INTERLY_CONFIG_DIR", str(tmp_path))

    output: list[str] = []
    answers = iter(["memory add name Ada", "y", "exit"])

    run_chat(
        model=OfflineModel(),
        read_input=lambda _prompt: next(answers),
        write_output=output.append,
    )

    store = MemoryStore(tmp_path / "memory.json")
    assert store.list_entries()[0]["key"] == "name"
    assert "Stored memory entry." in output


def test_groq_model_returns_text_from_client() -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Hello from Groq"))]
    )

    class FakeCompletions:
        def create(self, **_arguments: object) -> object:
            return response

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    model = GroqModel(api_key="test-key", model="test-model", client=fake_client)

    assert model.reply([{"role": "user", "content": "Hello"}]).content == "Hello from Groq"


def test_tool_requires_explicit_approval() -> None:
    class ToolCallingModel:
        def __init__(self) -> None:
            self.calls = 0

        def reply(self, _messages: list[dict[str, object]]) -> ModelTurn:
            self.calls += 1
            if self.calls == 1:
                request = ToolRequest(id="call-1", name="get_current_time", arguments="{}")
                return ModelTurn(
                    content=None,
                    tool_requests=[request],
                    assistant_message={
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": request.id,
                                "type": "function",
                                "function": {"name": request.name, "arguments": "{}"},
                            }
                        ],
                    },
                )
            return ModelTurn(
                content="Finished",
                tool_requests=[],
                assistant_message={"role": "assistant", "content": "Finished"},
            )

    answers = iter(["What time is it?", "n", "exit"])
    history = run_chat(ToolCallingModel(), lambda _prompt: next(answers), lambda _text: None)

    tool_message = next(message for message in history if message["role"] == "tool")
    assert "denied" in str(tool_message["content"])


@patch("computer_agent.chat.execute_tool", return_value="done")
@patch("computer_agent.chat.monotonic", return_value=100.0)
def test_set_free_temporarily_skips_approval_prompts(
    _monotonic: object, execute: object
) -> None:
    class ToolCallingModel:
        def __init__(self) -> None:
            self.calls = 0

        def reply(self, _messages: list[dict[str, object]]) -> ModelTurn:
            self.calls += 1
            if self.calls == 1:
                request = ToolRequest(id="call-1", name="get_current_time", arguments="{}")
                return ModelTurn(
                    content=None,
                    tool_requests=[request],
                    assistant_message={"role": "assistant", "content": None},
                )
            return ModelTurn(
                content="Finished",
                tool_requests=[],
                assistant_message={"role": "assistant", "content": "Finished"},
            )

    prompts: list[str] = []
    answers = iter(["set-free 5", "What time is it?", "exit"])

    run_chat(
        ToolCallingModel(),
        lambda prompt: prompts.append(prompt) or next(answers),
        lambda _text: None,
    )

    assert execute.call_count == 1
    assert not any(prompt.startswith("Allow?") for prompt in prompts)


@patch("computer_agent.chat.execute_tool")
def test_set_free_zero_restores_approval_prompts(execute: object) -> None:
    class ToolCallingModel:
        def __init__(self) -> None:
            self.calls = 0

        def reply(self, _messages: list[dict[str, object]]) -> ModelTurn:
            self.calls += 1
            if self.calls == 1:
                request = ToolRequest(id="call-1", name="get_current_time", arguments="{}")
                return ModelTurn(
                    content=None,
                    tool_requests=[request],
                    assistant_message={"role": "assistant", "content": None},
                )
            return ModelTurn(
                content="Finished",
                tool_requests=[],
                assistant_message={"role": "assistant", "content": "Finished"},
            )

    answers = iter(["set-free 5", "set-free 0", "What time is it?", "n", "exit"])
    history = run_chat(
        ToolCallingModel(),
        lambda _prompt: next(answers),
        lambda _text: None,
    )

    assert execute.call_count == 0
    tool_message = next(message for message in history if message["role"] == "tool")
    assert "denied" in str(tool_message["content"])


def test_set_free_rejects_values_above_thirty_minutes() -> None:
    output: list[str] = []
    answers = iter(["set-free 31", "exit"])

    run_chat(
        OfflineModel(),
        lambda _prompt: next(answers),
        output.append,
    )

    assert "Usage: set-free <1-30 whole minutes>, or set-free 0 to disable." in output


@patch("computer_agent.chat.execute_tool", return_value="safe web result")
def test_web_access_can_be_approved_for_session(execute: object) -> None:
    class WebModel:
        def __init__(self) -> None:
            self.calls = 0

        def reply(self, _messages: list[dict[str, object]]) -> ModelTurn:
            self.calls += 1
            if self.calls == 1:
                request = ToolRequest(id="search", name="search_web", arguments='{"query":"x"}')
            elif self.calls == 2:
                request = ToolRequest(
                    id="read", name="read_webpage", arguments='{"url":"https://example.com"}'
                )
            else:
                return ModelTurn(
                    content="Finished",
                    tool_requests=[],
                    assistant_message={"role": "assistant", "content": "Finished"},
                )
            return ModelTurn(
                content=None,
                tool_requests=[request],
                assistant_message={
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": request.id,
                            "type": "function",
                            "function": {"name": request.name, "arguments": request.arguments},
                        }
                    ],
                },
            )

    answers = iter(["Find something", "a", "exit"])
    run_chat(WebModel(), lambda _prompt: next(answers), lambda _text: None)

    assert execute.call_count == 2


def test_groq_command_reconfigures_locally_without_calling_model() -> None:
    model = OfflineModel()
    model.reply = lambda _messages: (_ for _ in ()).throw(AssertionError("model was called"))
    answers = iter(["groq", "exit"])
    reconfigured: list[bool] = []

    run_chat(
        model,
        lambda _prompt: next(answers),
        lambda _text: None,
        reconfigure_groq=lambda: reconfigured.append(True) or True,
    )

    assert reconfigured == [True]


@patch(
    "computer_agent.chat.execute_tool",
    return_value=LocalOnlyResult(
        model_status="Local report completed without sharing data.",
        terminal_output="PRIVATE-IP-192.0.2.1",
    ),
)
def test_local_only_output_is_printed_but_never_added_to_model_messages(_execute: object) -> None:
    class PrivacyCheckingModel:
        def __init__(self) -> None:
            self.calls = 0

        def reply(self, messages: list[dict[str, object]]) -> ModelTurn:
            self.calls += 1
            assert "PRIVATE-IP-192.0.2.1" not in str(messages)
            if self.calls == 1:
                request = ToolRequest(
                    id="private", name="run_read_command", arguments='{"command":"ipconfig"}'
                )
                return ModelTurn(
                    content=None,
                    tool_requests=[request],
                    assistant_message={"role": "assistant", "content": None},
                )
            return ModelTurn(
                content="The local result is displayed above.",
                tool_requests=[],
                assistant_message={"role": "assistant", "content": "Done"},
            )

    output: list[str] = []
    answers = iter(["Show IP information", "y", "exit"])
    history = run_chat(
        PrivacyCheckingModel(),
        lambda _prompt: next(answers),
        output.append,
    )

    assert any("PRIVATE-IP-192.0.2.1" in line for line in output)
    assert "PRIVATE-IP-192.0.2.1" not in str(history)


@patch(
    "computer_agent.chat.execute_tool",
    return_value=LocalOnlyResult(
        model_status="Local report completed.",
        terminal_output="AUTHORIZED-SYSTEM-DATA",
    ),
)
def test_sensitive_a_approval_explicitly_shares_output_with_model(_execute: object) -> None:
    class AccessCheckingModel:
        def __init__(self) -> None:
            self.calls = 0

        def reply(self, messages: list[dict[str, object]]) -> ModelTurn:
            self.calls += 1
            if self.calls == 1:
                request = ToolRequest(
                    id="private", name="read_system_metrics", arguments="{}"
                )
                return ModelTurn(
                    content=None,
                    tool_requests=[request],
                    assistant_message={"role": "assistant", "content": None},
                )
            assert "AUTHORIZED-SYSTEM-DATA" in str(messages)
            return ModelTurn(
                content="Authorized data processed.",
                tool_requests=[],
                assistant_message={"role": "assistant", "content": "Done"},
            )

    answers = iter(["Show metrics", "a", "exit"])
    history = run_chat(
        AccessCheckingModel(),
        lambda _prompt: next(answers),
        lambda _text: None,
    )

    assert "AUTHORIZED-SYSTEM-DATA" in str(history)


@patch("computer_agent.chat.BROWSER.close")
@patch("computer_agent.chat.execute_tool", return_value="Browser opened")
def test_isolated_browser_closes_after_browser_assisted_request(
    _execute: object, close_browser: object
) -> None:
    class BrowserModel:
        def __init__(self) -> None:
            self.calls = 0

        def reply(self, _messages: list[dict[str, object]]) -> ModelTurn:
            self.calls += 1
            if self.calls == 1:
                request = ToolRequest(
                    id="browser",
                    name="browser_open_url",
                    arguments='{"url":"https://example.com"}',
                )
                return ModelTurn(
                    content=None,
                    tool_requests=[request],
                    assistant_message={"role": "assistant", "content": None},
                )
            return ModelTurn(
                content="I read the page.",
                tool_requests=[],
                assistant_message={"role": "assistant", "content": "I read the page."},
            )

    answers = iter(["Open the page", "y", "exit"])
    run_chat(BrowserModel(), lambda _prompt: next(answers), lambda _text: None)

    close_browser.assert_called_once_with()
