"""Host-side execution governance for Interly."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from computer_agent.config import audit_log_file, permission_policy_file

POLICY_MODES = {"prompt", "allow", "deny"}
SENSITIVE_ARGUMENT_KEYS = {
    "content",
    "new_text",
    "old_text",
    "password",
    "secret",
    "text",
    "token",
    "value",
}
AUDIT_REDACT_ACTION_TOOLS = {
    "browser_type_text",
    "clipboard_write",
    "create_text_file",
    "desktop_keyboard",
    "edit_text_file",
}


@dataclass(frozen=True)
class PlanStep:
    """One user-visible step in a model-proposed plan."""

    action: str
    tool: str
    scope: str = ""


@dataclass(frozen=True)
class ApprovedPlan:
    """A plan approval that lasts for one user request only."""

    title: str
    steps: tuple[PlanStep, ...]

    def allows(self, tool: str, arguments: str) -> bool:
        """Return whether this exact tool call falls inside the approved plan scope."""
        argument_values = _argument_string_values(arguments)
        for step in self.steps:
            if step.tool != tool:
                continue
            if not step.scope:
                return True
            scope = step.scope.casefold()
            if any(scope in value.casefold() for value in argument_values):
                return True
        return False


class PermissionPolicyStore:
    """Persist simple prompt/allow/deny policy overrides per tool."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or permission_policy_file()

    def load(self) -> dict[str, Any]:
        """Load a valid policy document, falling back to safe defaults."""
        if not self.path.exists():
            return {"default": "prompt", "tools": {}}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"default": "prompt", "tools": {}}
        default = str(raw.get("default", "prompt"))
        if default not in POLICY_MODES:
            default = "prompt"
        tools = {
            str(name): str(mode)
            for name, mode in dict(raw.get("tools", {})).items()
            if str(mode) in POLICY_MODES
        }
        return {"default": default, "tools": tools}

    def mode_for(self, tool: str) -> str:
        policy = self.load()
        return str(policy["tools"].get(tool, policy["default"]))

    def set_mode(self, target: str, mode: str) -> Path:
        if mode not in POLICY_MODES:
            raise ValueError("Policy mode must be prompt, allow, or deny.")
        policy = self.load()
        if target == "default":
            policy["default"] = mode
        else:
            policy["tools"][target] = mode
        self._write(policy)
        return self.path

    def reset(self) -> Path:
        self._write({"default": "prompt", "tools": {}})
        return self.path

    def describe(self) -> str:
        policy = self.load()
        lines = [f"Default permission policy: {policy['default']}"]
        tools = dict(policy["tools"])
        if not tools:
            lines.append("No per-tool overrides.")
        else:
            lines.append("Per-tool overrides:")
            for tool in sorted(tools):
                lines.append(f"- {tool}: {tools[tool]}")
        return "\n".join(lines)

    def _write(self, policy: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")


class ActionAuditLog:
    """Append privacy-aware action records without storing raw sensitive payloads or outputs."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or audit_log_file()

    def record(
        self,
        *,
        tool: str,
        arguments: str,
        action: str,
        decision: str,
        outcome: str,
        request_id: str = "",
        plan_title: str = "",
    ) -> None:
        safe_action = (
            f"{tool} (sensitive action details redacted)"
            if tool in AUDIT_REDACT_ACTION_TOOLS
            else action[:1000]
        )
        entry = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "request_id": request_id,
            "tool": tool,
            "action": safe_action,
            "arguments": redact_arguments(arguments),
            "decision": decision,
            "outcome": outcome,
        }
        if plan_title:
            entry["plan"] = plan_title[:300]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def tail(self, limit: int = 20) -> str:
        if not self.path.exists():
            return "No audited actions yet."
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            return f"Could not read audit log: {error}"
        entries = lines[-max(1, min(limit, 100)) :]
        rendered: list[str] = []
        for line in entries:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            rendered.append(
                f"{entry.get('timestamp', '?')} | {entry.get('tool', '?')} | "
                f"{entry.get('decision', '?')} | {entry.get('outcome', '?')} | "
                f"{entry.get('action', '')}"
            )
        return "\n".join(rendered) if rendered else "No readable audited actions yet."


def parse_plan(arguments: str, known_tools: set[str]) -> tuple[str, tuple[PlanStep, ...]]:
    """Validate and parse a model-proposed plan."""
    try:
        payload = json.loads(arguments or "{}")
    except json.JSONDecodeError as error:
        raise ValueError("Plan arguments were invalid JSON.") from error
    title = str(payload.get("title", "")).strip()
    raw_steps = payload.get("steps", [])
    if not title or not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("A plan requires a title and at least one step.")
    if len(raw_steps) > 12:
        raise ValueError("A plan may contain at most 12 steps.")
    steps: list[PlanStep] = []
    for raw in raw_steps:
        if not isinstance(raw, dict):
            raise TypeError("Every plan step must be an object.")
        tool = str(raw.get("tool", "")).strip()
        action = str(raw.get("action", "")).strip()
        scope = str(raw.get("scope", "")).strip()
        if tool not in known_tools or tool == "propose_plan":
            raise ValueError(f"Plan referenced unavailable tool: {tool or '<empty>'}")
        if not action:
            raise ValueError("Every plan step requires a visible action description.")
        steps.append(PlanStep(action=action[:500], tool=tool, scope=scope[:500]))
    return title[:300], tuple(steps)


def render_plan(title: str, steps: tuple[PlanStep, ...]) -> str:
    lines = [f"Plan: {title}"]
    for index, step in enumerate(steps, start=1):
        scope = f" | scope: {step.scope}" if step.scope else ""
        lines.append(f"{index}. {step.action} [{step.tool}]{scope}")
    return "\n".join(lines)


def redact_arguments(arguments: str) -> dict[str, Any] | str:
    """Return a safe audit representation of tool arguments."""
    try:
        payload = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return "<invalid-json>"
    return _redact_value(payload)


def _redact_value(value: Any, key: str = "") -> Any:
    lowered_key = key.casefold()
    if lowered_key in SENSITIVE_ARGUMENT_KEYS:
        if isinstance(value, str):
            return f"<redacted:{len(value)} chars>"
        return "<redacted>"
    if lowered_key == "url" and isinstance(value, str):
        return _safe_url(value)
    if isinstance(value, dict):
        return {
            str(item_key): _redact_value(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item) for item in value[:50]]
    if isinstance(value, str) and len(value) > 1000:
        return value[:1000] + "<truncated>"
    return value


def _safe_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<invalid-url>"
    if not parsed.scheme or not parsed.hostname:
        return "<invalid-url>"
    hostname = parsed.hostname
    if parsed.port:
        hostname = f"{hostname}:{parsed.port}"
    return urlunsplit((parsed.scheme, hostname, parsed.path, "", ""))


def _argument_string_values(arguments: str) -> list[str]:
    try:
        payload = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return [arguments]
    values: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, dict):
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    collect(payload)
    return values
