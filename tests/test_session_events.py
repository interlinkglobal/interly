from computer_agent.session_events import ApprovalRequest, SessionEvent, new_request_id


def test_session_event_serializes_transport_neutral_shape() -> None:
    request_id = new_request_id()
    event = SessionEvent(
        request_id=request_id,
        type="tool.completed",
        capability="device.apps.open",
        message="Calculator opened",
        data={"application": "Calculator"},
    )

    payload = event.to_dict()

    assert payload["request_id"] == request_id
    assert payload["type"] == "tool.completed"
    assert payload["capability"] == "device.apps.open"
    assert payload["environment"] == "device"
    assert payload["data"] == {"application": "Calculator"}
    assert payload["event_id"]
    assert payload["timestamp"]


def test_approval_request_becomes_host_renderable_event() -> None:
    approval = ApprovalRequest(
        request_id="req-1",
        tool_name="open_application",
        capability="device.apps.open",
        action="Open Calculator",
        reason="Requested by the user",
        warnings=("Application launch changes desktop state.",),
    )

    event = approval.to_event()

    assert event.type == "approval.required"
    assert event.capability == "device.apps.open"
    assert event.data["tool_name"] == "open_application"
    assert event.data["warnings"] == ["Application launch changes desktop state."]
