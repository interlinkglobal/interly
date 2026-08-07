import json

from computer_agent.chat import run_chat
from computer_agent.models import ModelTurn, ToolRequest


class ScriptedModel:
    def __init__(self, turns):
        self.turns = iter(turns)

    def reply(self, _messages):
        return next(self.turns)


def turn_with_tool(tool_id, name, arguments):
    request = ToolRequest(id=tool_id, name=name, arguments=json.dumps(arguments))
    return ModelTurn(
        content=None,
        tool_requests=[request],
        assistant_message={
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_id,
                    "type": "function",
                    "function": {"name": name, "arguments": request.arguments},
                }
            ],
        },
    )


def final_turn(content="done"):
    return ModelTurn(
        content=content,
        tool_requests=[],
        assistant_message={"role": "assistant", "content": content},
    )


def scripted_input(values, prompts):
    iterator = iter(values)

    def reader(prompt):
        prompts.append(prompt)
        return next(iterator)

    return reader


def test_dry_run_never_calls_executor(tmp_path, monkeypatch):
    monkeypatch.setenv("INTERLY_CONFIG_DIR", str(tmp_path))

    def should_not_execute(*_args, **_kwargs):
        raise AssertionError("executor must not run during dry-run")

    monkeypatch.setattr("computer_agent.chat.execute_tool", should_not_execute)
    model = ScriptedModel(
        [
            turn_with_tool("tool-1", "get_current_time", {}),
            final_turn(),
        ]
    )
    prompts = []
    output = []

    run_chat(
        model,
        read_input=scripted_input(["dry-run on", "test", "y", "exit"], prompts),
        write_output=output.append,
    )

    assert any("DRY RUN" in message for message in output)
    audit_text = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert '"outcome": "dry-run"' in audit_text


def test_approved_plan_scopes_matching_tool_without_second_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("INTERLY_CONFIG_DIR", str(tmp_path))
    calls = []

    def fake_execute(name, arguments):
        calls.append((name, arguments))
        return "read completed"

    monkeypatch.setattr("computer_agent.chat.execute_tool", fake_execute)
    plan_arguments = {
        "title": "Read project file",
        "steps": [
            {
                "action": "Read README",
                "tool": "read_text_file",
                "scope": r"C:\work\project",
            }
        ],
    }
    model = ScriptedModel(
        [
            turn_with_tool("plan-1", "propose_plan", plan_arguments),
            turn_with_tool(
                "tool-1",
                "read_text_file",
                {"path": r"C:\work\project\README.md"},
            ),
            final_turn(),
        ]
    )
    prompts = []

    run_chat(
        model,
        read_input=scripted_input(["inspect", "y", "exit"], prompts),
        write_output=lambda _message: None,
    )

    assert [name for name, _arguments in calls] == ["read_text_file"]
    assert sum("Approve this plan" in prompt for prompt in prompts) == 1
    assert not any(prompt.startswith("Allow?") for prompt in prompts)


def test_policy_deny_blocks_tool_without_execution(tmp_path, monkeypatch):
    monkeypatch.setenv("INTERLY_CONFIG_DIR", str(tmp_path))

    def should_not_execute(*_args, **_kwargs):
        raise AssertionError("policy-denied tool must not execute")

    monkeypatch.setattr("computer_agent.chat.execute_tool", should_not_execute)
    model = ScriptedModel(
        [
            turn_with_tool("tool-1", "get_current_time", {}),
            final_turn(),
        ]
    )
    prompts = []
    output = []

    run_chat(
        model,
        read_input=scripted_input(
            ["policy set get_current_time deny", "test", "exit"],
            prompts,
        ),
        write_output=output.append,
    )

    assert any("Permission policy denied" in message for message in output)
    assert not any(prompt.startswith("Allow?") for prompt in prompts)
