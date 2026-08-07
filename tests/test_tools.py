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
    open_executable_command,
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


@patch("computer_agent.tools.subprocess.Popen")
@patch("computer_agent.tools.resolve_executable_command")
def test_explicit_executable_command_is_resolved_before_launch(resolve: object, popen: object) -> None:
    resolve.return_value = [r"C:\Program Files\Google\Chrome\Application\chrome.exe"]

    result = open_executable_command("chrome.exe")

    assert "Opened executable" in result
    resolve.assert_called_once_with("chrome.exe")
    popen.assert_called_once_with(
        [r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
    )


@patch("computer_agent.tools.subprocess.Popen")
def test_executable_command_rejects_shell_syntax(popen: object) -> None:
    result = open_executable_command("chrome & calc")

    assert "nothing was opened" in result
    popen.assert_not_called()


def test_executable_command_schema_accepts_one_token_only() -> None:
    schema = next(
        tool for tool in TOOL_SCHEMAS if tool["function"]["name"] == "open_executable_command"
    )

    assert schema["function"]["parameters"]["required"] == ["command_name"]


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


def test_download_tool_requires_url_and_exact_destination() -> None:
    schema = next(
        tool for tool in TOOL_SCHEMAS if tool["function"]["name"] == "download_public_file"
    )

    assert schema["function"]["parameters"]["required"] == ["url", "destination"]


@patch("computer_agent.tools.download_public_file", return_value="downloaded")
def test_download_tool_executes_only_after_dispatch(download: object) -> None:
    result = execute_tool(
        "download_public_file",
        '{"url":"https://example.com/video.mp4","destination":"C:/Downloads/video.mp4"}',
    )

    assert result == "downloaded"
    download.assert_called_once_with(
        "https://example.com/video.mp4", "C:/Downloads/video.mp4"
    )


@patch("computer_agent.tools.read_text_file", return_value="private file data")
def test_file_read_is_local_only_by_default(_read: object) -> None:
    result = execute_tool("read_text_file", '{"path":"C:/private.txt"}')

    assert isinstance(result, LocalOnlyResult)
    assert result.terminal_output == "private file data"
    assert "private file data" not in result.model_status


def test_repository_workflow_tools_are_described_and_executed(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    repo_json = str(repo).replace("\\", "\\\\")
    action, reason, warning = describe_tool("inspect_repository", f'{{"root": "{repo_json}"}}')
    assert "Inspect repository" in action
    assert reason == "List repository files and structure"
    assert warning is None

    result = execute_tool("inspect_repository", f'{{"root": "{repo_json}"}}')
    assert "pyproject.toml" in result

    command_result = execute_tool(
        "run_repository_command",
        f'{{"root": "{repo_json}", "command": ["python", "-c", "print(1)"], "timeout": 5}}',
    )
    assert '"returncode": 0' in command_result
