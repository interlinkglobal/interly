"""Transport-neutral event contract for Interly agent sessions.

The terminal host, future Okay Device Gateway host, and tests should consume the
same event vocabulary. This module intentionally contains no networking code and
no UI concerns; Interly remains the local execution and governance authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

SessionEventType = Literal[
    "operation.started",
    "operation.progress",
    "tool.requested",
    "tool.completed",
    "approval.required",
    "artifact.created",
    "operation.failed",
    "operation.completed",
]


@dataclass(frozen=True, slots=True)
class SessionEvent:
    """One structured observation emitted by the Interly runtime."""

    request_id: str
    type: SessionEventType
    message: str
    capability: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    environment: Literal["device"] = "device"

    def to_dict(self) -> dict[str, Any]:
        """Return the language-neutral representation used by hosts/transports."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    """A host-renderable approval while enforcement remains inside Interly."""

    request_id: str
    tool_name: str
    capability: str
    action: str
    reason: str
    warnings: tuple[str, ...] = ()

    def to_event(self) -> SessionEvent:
        return SessionEvent(
            request_id=self.request_id,
            type="approval.required",
            capability=self.capability,
            message=self.action,
            data={
                "tool_name": self.tool_name,
                "reason": self.reason,
                "warnings": list(self.warnings),
            },
        )


def new_request_id() -> str:
    """Create an opaque correlation identifier for one submitted user request."""
    return str(uuid4())
