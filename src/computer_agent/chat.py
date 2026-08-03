"""The Stage 1 terminal conversation loop."""

from collections.abc import Callable
from typing import Any

from playwright.sync_api import Error as PlaywrightError

from computer_agent.emergency import EmergencyStop
from computer_agent.models import AuthenticationModelError, ChatModel, ModelError
from computer_agent.tools import LocalOnlyResult, describe_tool, execute_tool

ReadInput = Callable[[str], str]
WriteOutput = Callable[[str], None]
ReconfigureGroq = Callable[[], bool]
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
}
PER_MESSAGE_TOOL_LIMITS = {
    "search_web": 2,
    "read_webpage": 5,
    "research_web": 1,
    "browser_open_url": 3,
    "browser_read_page": 5,
}
MAX_MODEL_ROUNDS_PER_MESSAGE = 12


def run_chat(
    model: ChatModel,
    read_input: ReadInput = input,
    write_output: WriteOutput = print,
    emergency_stop: EmergencyStop | None = None,
    reconfigure_groq: ReconfigureGroq | None = None,
) -> list[dict[str, Any]]:
    """Chat until the user exits, then return the conversation history."""
    messages: list[dict[str, Any]] = []
    session_approvals: set[str] = set()
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

        if not user_text:
            continue
        if emergency_stop and emergency_stop.requested():
            write_output("Emergency stop: request cancelled.")
            continue

        messages.append({"role": "user", "content": user_text})
        tool_counts: dict[str, int] = {}
        model_rounds = 0

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
                if approval_group in session_approvals:
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

    return messages
