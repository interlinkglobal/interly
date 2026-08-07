import json

from computer_agent.runtime_tools import (
    TOOL_NAMES,
    LocalOnlyResult,
    describe_tool,
    execute_tool,
)


def test_runtime_registry_contains_governance_and_desktop_tools():
    expected = {
        "propose_plan",
        "desktop_list_windows",
        "desktop_window_action",
        "desktop_screenshot",
        "desktop_ocr",
        "desktop_inspect_controls",
        "clipboard_read",
        "clipboard_write",
        "desktop_mouse",
        "desktop_keyboard",
    }
    assert expected <= TOOL_NAMES


def test_desktop_list_windows_is_local_only(monkeypatch):
    monkeypatch.setattr(
        "computer_agent.runtime_tools.list_windows",
        lambda: '[{"window_handle": 1, "title": "Example"}]',
    )

    result = execute_tool("desktop_list_windows", "{}")

    assert isinstance(result, LocalOnlyResult)
    assert "Example" in result.terminal_output
    assert "only in the user's terminal" in result.model_status


def test_describe_keyboard_does_not_hide_user_preview():
    action, reason, warning = describe_tool(
        "desktop_keyboard",
        json.dumps({"action": "press", "keys": ["ctrl", "s"]}),
    )

    assert "ctrl" in action
    assert "keyboard" in reason.casefold()
    assert warning is not None


def test_runtime_delegates_existing_tool():
    result = execute_tool("get_current_time", "{}")
    assert "Local datetime:" in result
