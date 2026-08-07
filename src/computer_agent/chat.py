"""The Stage 1 terminal conversation loop."""

from collections.abc import Callable
from time import monotonic
from typing import Any

from playwright.sync_api import Error as PlaywrightError

from computer_agent.browser import BROWSER
from computer_agent.emergency import EmergencyStop
from computer_agent.memory import MemoryStore
from computer_agent.models import AuthenticationModelError, ChatModel, ModelError
from computer_agent.tools import LocalOnlyResult, describe_tool, execute_tool

ReadInput = Callable[[str], str]
WriteOutput = Callable[[str], None]
ReconfigureGroq = Callable[[], bool]
UpdateInterly = Callable[[], str]
EXIT_COMMANDS = {"exit", "quit", "/exit"}
SESSION_APPROVAL_GROUPS = {
    "search_web": "direct web access",
    "read_webpage": "direct web access",
    "research_web": "direct web access",
}
SENSITIVE_LOCAL_TOOLS = {
    "find_applications",
    "find_processes",
    "read_installed_applications",
    "read_system_metrics",
    "run_read_command",
    "search_files",
    "read_text_file",
    "compare_files",
}
PER_MESSAGE_TOOL_LIMITS = {
    "search_web": 2,
    "read_webpage": 5,
    "research_web": 1,
    "browser_open_url": 3,
    "browser_read_page": 5,
}
MAX_MODEL_ROUNDS_PER_MESSAGE = 12
SET_FREE_COMMAND = "set-free"
MAX_SET_FREE_MINUTES = 30


def run_chat(
    model: ChatModel,
    read_input: ReadInput = input,
    write_output: WriteOutput = print,
    emergency_stop: EmergencyStop | None = None,
    reconfigure_groq: ReconfigureGroq | None = None,
    update_interly: UpdateInterly | None = None,
) -> list[dict[str, Any]]:
    """Chat until the user exits, then return the conversation history."""
    messages: list[dict[str, Any]] = []
    session_approvals: set[str] = set()
    free_until: float | None = None
    memory_store = MemoryStore()
    write_output("Interlink is ready. Type 'exit' to stop.")

    while True:
        if emergency_stop:
            emergency_stop.reset()
        try:
            # PowerShell can prepend a Unicode marker when input is piped into Python.
            user_text = read_input("You: ").strip().lstrip("\ufeff")
        except (EOFError, KeyboardInterrupt):
            write_output("\nGoodbye!")
            break

        if user_text.lower() in EXIT_COMMANDS:
            write_output("Goodbye!")
            break

        if user_text.casefold() == "groq":
            if reconfigure_groq is None:
                write_output("Groq key replacement is unavailable in this mode.")
            elif reconfigure_groq():
                write_output("Groq API key replaced. The current Interlink session is ready.")
            else:
                write_output("Groq API key was not changed.")
            continue

        if user_text.casefold() == "update":
            if update_interly is None:
                write_output("Interly updates are unavailable in this mode.")
            else:
                write_output("Checking the Interly repository for updates...")
                write_output(update_interly())
            continue

        if user_text.casefold().startswith(f"{SET_FREE_COMMAND} "):
            value = user_text[len(SET_FREE_COMMAND) :].strip()
            try:
                minutes = int(value)
                if minutes < 0 or minutes > MAX_SET_FREE_MINUTES:
                    raise ValueError
            except ValueError:
                write_output("Usage: set-free <1-30 whole minutes>, or set-free 0 to disable.")
                continue
            if minutes == 0:
                free_until = None
                write_output("Automatic command approval disabled.")
            else:
                free_until = monotonic() + minutes * 60
                write_output(
                    f"Automatic command approval enabled for {minutes} minute"
                    f"{'s' if minutes != 1 else ''}. Emergency stop remains active."
                )
            continue

        if user_text.casefold() == "memory":
            entries = memory_store.list_entries()
            if entries:
                write_output("Stored memory:")
                for entry in entries:
                    write_output(f"- {entry['key']}: {entry['value']}")
            else:
                write_output("No memory entries stored.")
            continue

        if not user_text:
            continue
        if emergency_stop and emergency_stop.requested():
            write_output("Emergency stop: request cancelled.")
            continue

        messages.append({"role": "user", "content": user_text})
        tool_counts: dict[str, int] = {}
        model_rounds = 0
        browser_used = False

        while True:
            if emergency_stop and emergency_stop.requested():
                write_output("Emergency stop: remaining actions cancelled.")
                break
            model_rounds += 1
            if model_rounds > MAX_MODEL_ROUNDS_PER_MESSAGE:
                write_output("Interlink stopped this request because it exceeded the tool limit.")
                break
            try:
                turn = model.reply(messages)
            except AuthenticationModelError as error:
                write_output(f"Error: {error}")
                break
            except ModelError as error:
                write_output(f"Error: {error}")
                break

            messages.append(turn.assistant_message)
            if turn.content:
                write_output(f"Agent: {turn.content}")

            if not turn.tool_requests:
                break

            for request in turn.tool_requests:
                share_sensitive_output = False
                if request.name.startswith("browser_"):
                    browser_used = True
                tool_counts[request.name] = tool_counts.get(request.name, 0) + 1
                limit = PER_MESSAGE_TOOL_LIMITS.get(request.name)
                if limit is not None and tool_counts[request.name] > limit:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": request.id,
                            "content": (
                                f"Per-question limit reached for {request.name}. Do not retry. "
                                "Answer using results already collected or explain the limitation."
                            ),
                        }
                    )
                    continue

                action, reason, warning = describe_tool(request.name, request.arguments)
                write_output(f"\nInterlink wants to: {action}")
                write_output(f"Reason: {reason}")
                if warning:
                    write_output(warning)
                approval_group = SESSION_APPROVAL_GROUPS.get(request.name)
                free_active = free_until is not None and monotonic() < free_until
                if free_until is not None and not free_active:
                    free_until = None
                    write_output("Automatic command approval period ended; prompts restored.")
                if free_active or approval_group in session_approvals:
                    approved = True
                else:
                    if request.name in SENSITIVE_LOCAL_TOOLS:
                        prompt = "Allow? [Y=local only/N=deny/A=allow Groq access]: "
                    elif approval_group:
                        prompt = f"Allow? [Y/N/A=allow {approval_group} for this session]: "
                    else:
                        prompt = "Allow? [Y/N]: "
                    try:
                        answer = read_input(prompt).strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        answer = ""
                    approved = answer in {"y", "a"}
                    share_sensitive_output = (
                        answer == "a" and request.name in SENSITIVE_LOCAL_TOOLS
                    )
                    if answer == "a" and approval_group and not share_sensitive_output:
                        session_approvals.add(approval_group)
                        write_output(f"Allowed {approval_group} for this Interlink session.")

                if emergency_stop and emergency_stop.requested():
                    result = "Emergency stop requested. No further actions may run."
                elif approved:
                    try:
                        result = execute_tool(request.name, request.arguments)
                    except (OSError, RuntimeError, ValueError, PlaywrightError) as error:
                        result = f"Tool failed safely: {error}"
                else:
                    result = "Permission denied by the user. The tool was not executed."
                if isinstance(result, LocalOnlyResult):
                    heading = (
                        "\nOutput (Groq access explicitly allowed):"
                        if share_sensitive_output
                        else "\nLocal-only output (not sent to Groq):"
                    )
                    write_output(heading)
                    write_output(result.terminal_output)
                    if share_sensitive_output:
                        model_result = (
                            "The local command completed. The user explicitly authorized Groq "
                            f"access to this command output:\n{result.terminal_output}"
                        )
                    else:
                        model_result = result.model_status
                else:
                    model_result = result
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": request.id,
                        "content": model_result,
                    }
                )

        if browser_used:
            try:
                BROWSER.close()
                write_output("Isolated browser closed.")
            except (OSError, RuntimeError, PlaywrightError) as error:
                write_output(f"Warning: isolated browser cleanup failed: {error}")

    return messages
