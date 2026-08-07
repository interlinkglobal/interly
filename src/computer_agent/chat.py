"""The Stage 1 terminal conversation loop."""

from collections.abc import Callable
from time import monotonic
from typing import Any

from playwright.sync_api import Error as PlaywrightError

from computer_agent.browser import BROWSER
from computer_agent.dev_workflows import WorkflowRegistry
from computer_agent.emergency import EmergencyStop
from computer_agent.governance import (
    ActionAuditLog,
    ApprovedPlan,
    PermissionPolicyStore,
    parse_plan,
    render_plan,
)
from computer_agent.memory import MemoryStore
from computer_agent.models import AuthenticationModelError, ChatModel, ModelError
from computer_agent.runtime_tools import (
    TOOL_NAMES,
    LocalOnlyResult,
    describe_tool,
    execute_tool,
)

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
    "clipboard_read",
    "compare_files",
    "desktop_inspect_controls",
    "desktop_list_windows",
    "desktop_ocr",
    "find_applications",
    "find_processes",
    "read_installed_applications",
    "read_system_metrics",
    "read_text_file",
    "run_read_command",
    "search_files",
}
ALWAYS_CONFIRM_TOOLS = {
    "close_or_kill_process",
    "logout_windows",
    "windows_power_action",
}
PER_MESSAGE_TOOL_LIMITS = {
    "search_web": 2,
    "read_webpage": 5,
    "research_web": 1,
    "browser_open_url": 3,
    "browser_read_page": 5,
    "desktop_screenshot": 5,
    "desktop_ocr": 5,
    "desktop_inspect_controls": 5,
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
    dry_run = False
    memory_store = MemoryStore()
    workflow_registry = WorkflowRegistry()
    policy_store = PermissionPolicyStore()
    audit_log = ActionAuditLog()
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

        lowered = user_text.casefold()
        if lowered in EXIT_COMMANDS:
            write_output("Goodbye!")
            break

        if lowered == "groq":
            if reconfigure_groq is None:
                write_output("Groq key replacement is unavailable in this mode.")
            elif reconfigure_groq():
                write_output("Groq API key replaced. The current Interlink session is ready.")
            else:
                write_output("Groq API key was not changed.")
            continue

        if lowered == "update":
            if update_interly is None:
                write_output("Interly updates are unavailable in this mode.")
            else:
                write_output("Checking the Interly repository for updates...")
                write_output(update_interly())
            continue

        if lowered in {"dry-run", "dry-run status"}:
            write_output(f"Dry-run mode is {'ON' if dry_run else 'OFF'}.")
            continue
        if lowered == "dry-run on":
            dry_run = True
            write_output("Dry-run mode enabled. Approved tools will be previewed but not executed.")
            continue
        if lowered == "dry-run off":
            dry_run = False
            write_output("Dry-run mode disabled. Approved tools may execute again.")
            continue

        if lowered == "policy":
            write_output(policy_store.describe())
            continue
        if lowered == "policy reset":
            policy_store.reset()
            write_output("Permission policies reset to prompt-by-default.")
            continue
        if lowered.startswith("policy set "):
            parts = user_text.split()
            if len(parts) != 4:
                write_output("Usage: policy set <default|tool_name> <prompt|allow|deny>")
                continue
            _, _, target, mode = parts
            target = target.strip()
            mode = mode.casefold()
            if target != "default" and target not in TOOL_NAMES:
                write_output(f"Unknown tool for permission policy: {target}")
                continue
            if target == "propose_plan":
                write_output("propose_plan is host-governed and cannot receive a policy override.")
                continue
            try:
                path = policy_store.set_mode(target, mode)
            except ValueError as error:
                write_output(str(error))
            else:
                write_output(f"Permission policy saved: {target} = {mode} ({path})")
            continue

        if lowered == "audit" or lowered.startswith("audit "):
            limit = 20
            if lowered.startswith("audit "):
                try:
                    limit = int(user_text.split(maxsplit=1)[1])
                except ValueError:
                    write_output("Usage: audit [1-100]")
                    continue
                if limit < 1 or limit > 100:
                    write_output("Usage: audit [1-100]")
                    continue
            write_output(audit_log.tail(limit))
            continue

        if lowered.startswith(f"{SET_FREE_COMMAND} "):
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
                    f"{'s' if minutes != 1 else ''}. Emergency stop remains active; "
                    "destructive Windows actions still ask individually."
                )
            continue

        if lowered == "memory":
            entries = memory_store.list_entries()
            if entries:
                write_output("Stored memory:")
                for entry in entries:
                    write_output(f"- {entry['key']}: {entry['value']}")
            else:
                write_output("No memory entries stored.")
            continue

        if lowered.startswith("memory add "):
            parts = user_text.split(maxsplit=3)
            if len(parts) == 4:
                _, _, key, value = parts
                memory_store.add_entry(key, value, approved=True)
                write_output("Stored memory entry.")
            else:
                write_output("Usage: memory add <key> <value>")
            continue

        if lowered == "memory export":
            write_output("Exported memory entries:")
            for entry in memory_store.export_entries():
                write_output(f"- {entry['key']}: {entry['value']}")
            continue

        if lowered == "memory clear":
            cleared = memory_store.clear_entries()
            write_output(f"Cleared {cleared} memory entries.")
            continue

        if lowered == "make-memory":
            target = memory_store.path.parent / "interly-memory.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text("[]\n", encoding="utf-8")
            write_output(f"interly-memory.txt created at {target}")
            continue

        if lowered.startswith("make-memory "):
            parts = user_text.split(maxsplit=2)
            if len(parts) == 3:
                _, _, description = parts
                target = memory_store.path.parent / "interly-memory.txt"
                entry = memory_store.save_beta_memory(target, description, description)
                write_output(f"I have saved {entry['value']!r} in interly-memory.txt")
            else:
                write_output("Usage: make-memory <value>")
            continue

        if lowered == "workflows":
            workflows = workflow_registry.list_workflows()
            if workflows:
                write_output("Saved workflows:")
                for workflow in workflows:
                    write_output(f"- {workflow['name']}")
            else:
                write_output("No saved workflows.")
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
        approved_plan: ApprovedPlan | None = None

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

                if request.name == "propose_plan":
                    try:
                        title, steps = parse_plan(request.arguments, TOOL_NAMES)
                    except ValueError as error:
                        model_result = f"Plan rejected by the host: {error}"
                        audit_log.record(
                            tool="propose_plan",
                            arguments=request.arguments,
                            action="Present multi-step execution plan",
                            decision="host-validation",
                            outcome="invalid-plan",
                            request_id=request.id,
                        )
                    else:
                        write_output("\n" + render_plan(title, steps))
                        try:
                            answer = read_input(
                                "Approve this plan for this request? [Y/N]: "
                            ).strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            answer = ""
                        if answer == "y":
                            approved_plan = ApprovedPlan(title=title, steps=steps)
                            model_result = (
                                "The user approved this displayed plan for the current request. "
                                "Calls inside its exact tool/scope boundaries may proceed without "
                                "another prompt except destructive Windows actions."
                            )
                            outcome = "approved"
                        else:
                            approved_plan = None
                            model_result = (
                                "The user denied the displayed plan. Do not execute its steps."
                            )
                            outcome = "denied"
                        audit_log.record(
                            tool="propose_plan",
                            arguments=request.arguments,
                            action=f"Present plan: {title}",
                            decision="user-plan-approval",
                            outcome=outcome,
                            request_id=request.id,
                            plan_title=title,
                        )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": request.id,
                            "content": model_result,
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

                policy_mode = policy_store.mode_for(request.name)
                plan_matches = (
                    approved_plan is not None
                    and approved_plan.allows(request.name, request.arguments)
                )
                must_confirm = request.name in ALWAYS_CONFIRM_TOOLS
                decision_source = "manual"
                approved = False

                if policy_mode == "deny":
                    decision_source = "policy-deny"
                elif not must_confirm and policy_mode == "allow":
                    approved = True
                    decision_source = "policy-allow"
                elif not must_confirm and plan_matches:
                    approved = True
                    decision_source = "approved-plan"
                elif not must_confirm and free_active:
                    approved = True
                    decision_source = "set-free"
                elif not must_confirm and approval_group in session_approvals:
                    approved = True
                    decision_source = "session-approval"
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
                    decision_source = "user-approve" if approved else "user-deny"
                    share_sensitive_output = (
                        answer == "a" and request.name in SENSITIVE_LOCAL_TOOLS
                    )
                    if answer == "a" and approval_group and not share_sensitive_output:
                        session_approvals.add(approval_group)
                        write_output(f"Allowed {approval_group} for this Interlink session.")

                if emergency_stop and emergency_stop.requested():
                    result: str | LocalOnlyResult = (
                        "Emergency stop requested. No further actions may run."
                    )
                    outcome = "emergency-stop"
                elif not approved:
                    if policy_mode == "deny":
                        result = "Permission policy denied this tool. The tool was not executed."
                    else:
                        result = "Permission denied by the user. The tool was not executed."
                    outcome = "denied"
                elif dry_run:
                    result = f"DRY RUN: approved but not executed. Would perform: {action}"
                    outcome = "dry-run"
                else:
                    try:
                        result = execute_tool(request.name, request.arguments)
                    except (OSError, RuntimeError, ValueError, PlaywrightError) as error:
                        result = f"Tool failed safely: {error}"
                        outcome = "failed"
                    else:
                        outcome = "executed"

                audit_log.record(
                    tool=request.name,
                    arguments=request.arguments,
                    action=action,
                    decision=decision_source,
                    outcome=outcome,
                    request_id=request.id,
                    plan_title=(
                        approved_plan.title
                        if approved_plan is not None and plan_matches
                        else ""
                    ),
                )

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
