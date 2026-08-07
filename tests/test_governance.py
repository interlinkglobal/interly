import json

import pytest

from computer_agent.governance import (
    ActionAuditLog,
    ApprovedPlan,
    PermissionPolicyStore,
    PlanStep,
    parse_plan,
    redact_arguments,
)


def test_permission_policy_store_defaults_and_overrides(tmp_path):
    store = PermissionPolicyStore(tmp_path / "permissions.json")

    assert store.mode_for("desktop_mouse") == "prompt"
    store.set_mode("desktop_mouse", "deny")
    assert store.mode_for("desktop_mouse") == "deny"
    store.set_mode("default", "allow")
    assert store.mode_for("desktop_keyboard") == "allow"
    assert store.mode_for("desktop_mouse") == "deny"

    store.reset()
    assert store.mode_for("desktop_mouse") == "prompt"


def test_permission_policy_store_rejects_unknown_mode(tmp_path):
    store = PermissionPolicyStore(tmp_path / "permissions.json")
    with pytest.raises(ValueError):
        store.set_mode("desktop_mouse", "sometimes")


def test_approved_plan_enforces_tool_and_scope():
    plan = ApprovedPlan(
        title="Inspect project",
        steps=(PlanStep("Read file", "read_text_file", r"C:\work\project"),),
    )

    assert plan.allows("read_text_file", '{"path":"C:\\\\work\\\\project\\\\README.md"}')
    assert not plan.allows("read_text_file", '{"path":"C:\\\\private\\\\notes.txt"}')
    assert not plan.allows("edit_text_file", '{"path":"C:\\\\work\\\\project\\\\README.md"}')


def test_parse_plan_rejects_unknown_tool():
    arguments = json.dumps(
        {
            "title": "Bad plan",
            "steps": [{"action": "Do it", "tool": "invented_tool"}],
        }
    )
    with pytest.raises(ValueError):
        parse_plan(arguments, {"read_text_file", "propose_plan"})


def test_redact_arguments_hides_payloads_and_url_queries():
    safe = redact_arguments(
        json.dumps(
            {
                "text": "private clipboard text",
                "url": "https://user:pass@example.com/path?token=secret#fragment",
                "path": r"C:\Users\Casey\file.txt",
            }
        )
    )

    assert safe["text"] == "<redacted:22 chars>"
    assert safe["url"] == "https://example.com/path"
    assert safe["path"] == r"C:\Users\Casey\file.txt"


def test_audit_log_redacts_sensitive_action_and_arguments(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    audit = ActionAuditLog(log_path)
    audit.record(
        tool="clipboard_write",
        arguments=json.dumps({"text": "top secret"}),
        action="Replace clipboard with 'top secret'",
        decision="user-approve",
        outcome="executed",
        request_id="tool-1",
    )

    entry = json.loads(log_path.read_text(encoding="utf-8"))
    assert "top secret" not in entry["action"]
    assert entry["arguments"]["text"] == "<redacted:10 chars>"
    assert "clipboard_write" in audit.tail()
