from unittest.mock import patch

from computer_agent.tools import (
    TOOL_SCHEMAS,
    LocalOnlyResult,
    close_or_kill_process,
    describe_tool,
    execute_tool,
    find_applications,
    find_processes,
    get_current_time,
    open_application,
    run_read_command,
)


def test_current_time_includes_timezone_name() -> None:
    result = get_current_time()

    assert "Local datetime:" in result
    assert "Local timezone name:" in result


@patch("computer_agent.tools.get_registered_applications")
def test_find_applications_matches_registered_name(get_apps: object) -> None:
    get_apps.return_value = [
        {"name": "Microsoft Edge", "application_id": "MSEdge"},
        {"name": "Notepad", "application_id": "Notepad-ID"},
    ]

    result = find_applications("Edge browser")

    assert "Microsoft Edge" in result
    assert "Notepad" not in result


@patch("computer_agent.tools.subprocess.Popen")
@patch("computer_agent.tools.get_registered_applications")
def test_open_registered_application(get_apps: object, popen: object) -> None:
    get_apps.return_value = [{"name": "Microsoft Edge", "application_id": "MSEdge"}]

    result = open_application("MSEdge", "Microsoft Edge")

    assert result == "Opened Microsoft Edge."
    popen.assert_called_once_with(["explorer.exe", r"shell:AppsFolder\MSEdge"])


@patch("computer_agent.tools.subprocess.Popen")
@patch("computer_agent.tools.get_registered_applications")
def test_invented_application_id_is_rejected(get_apps: object, popen: object) -> None:
    get_apps.return_value = [{"name": "Microsoft Edge", "application_id": "MSEdge"}]

    result = open_application("powershell.exe", "PowerShell")

    assert "nothing was opened" in result
    popen.assert_not_called()


@patch("computer_agent.tools.get_running_processes")
def test_find_processes_returns_exact_pid(get_processes: object) -> None:
    get_processes.return_value = [
        {"Id": 101, "ProcessName": "notepad", "MainWindowTitle": "Notes"},
        {"Id": 202, "ProcessName": "chrome", "MainWindowTitle": "Browser"},
    ]

    result = find_processes("close notepad")

    assert '"process_id": 101' in result
    assert '"process_id": 202' not in result


@patch("computer_agent.tools.subprocess.run")
@patch("computer_agent.tools.get_running_processes")
def test_close_process_uses_exact_pid(get_processes: object, run: object) -> None:
    get_processes.return_value = [
        {"Id": 101, "ProcessName": "notepad", "MainWindowTitle": "Notes"}
    ]
    run.return_value.stdout = "SUCCESS"
    run.return_value.stderr = ""
    run.return_value.returncode = 0

    result = close_or_kill_process("close", 101, "notepad")

    assert "SUCCESS" in result
    assert run.call_args.args[0] == ["taskkill.exe", "/PID", "101"]


@patch("computer_agent.tools.subprocess.run")
@patch("computer_agent.tools.get_running_processes")
def test_critical_process_is_blocked(get_processes: object, run: object) -> None:
    get_processes.return_value = [
        {"Id": 500, "ProcessName": "lsass", "MainWindowTitle": ""}
    ]

    result = close_or_kill_process("kill", 500, "lsass")

    assert "blocks" in result
    run.assert_not_called()


def test_logout_preview_contains_strong_warning() -> None:
    action, _reason, warning = describe_tool("logout_windows", "{}")

    assert action == "Run: shutdown.exe /l"
    assert warning is not None
    assert "Unsaved work" in warning


@patch("computer_agent.tools.subprocess.run")
def test_process_read_command_counts_rows(run: object) -> None:
    run.return_value.stdout = '"one.exe","1"\n"two.exe","2"\n'
    run.return_value.stderr = ""
    run.return_value.returncode = 0

    result = run_read_command("processes")

    assert "Running process count: 2" in result
    run.assert_called_once()


@patch("computer_agent.tools.subprocess.run")
def test_unlisted_read_command_never_reaches_windows(run: object) -> None:
    result = run_read_command("delete_everything")

    assert "not allowed" in result
    run.assert_not_called()


@patch("computer_agent.tools.run_read_command", return_value="private output")
def test_read_command_execution_returns_local_only_result(_read: object) -> None:
    result = execute_tool("run_read_command", '{"command":"ipconfig"}')

    assert isinstance(result, LocalOnlyResult)
    assert result.terminal_output == "private output"
    assert "private output" not in result.model_status


def test_browser_read_tool_requires_explicit_valid_json_argument() -> None:
    schema = next(
        tool for tool in TOOL_SCHEMAS if tool["function"]["name"] == "browser_read_page"
    )

    assert schema["function"]["parameters"]["required"] == ["mode"]


def test_browser_click_requires_control_preview() -> None:
    schema = next(
        tool for tool in TOOL_SCHEMAS if tool["function"]["name"] == "browser_click_control"
    )

    assert schema["function"]["parameters"]["required"] == [
        "control_id",
        "control_description",
    ]


@patch("computer_agent.tools.read_text_file", return_value="private file data")
def test_file_read_is_local_only_by_default(_read: object) -> None:
    result = execute_tool("read_text_file", '{"path":"C:/private.txt"}')

    assert isinstance(result, LocalOnlyResult)
    assert result.terminal_output == "private file data"
    assert "private file data" not in result.model_status
