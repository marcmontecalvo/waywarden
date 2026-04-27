"""Approval hooks wrapping the tool registry for coding operations.

Every coded-operation approval (file writes, shell exec, network egress)
is routed through the P3 approval engine with explicit RT-002 mapping
and no bypass paths.   Pending approvals rendered visible.

Canonical references:
    ADR 0005
    RT-002 §Approval event mapping
    P6-1 #92
"""

from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger

from waywarden.domain.manifest.tool_policy import ToolPolicy
from waywarden.services.approval_engine import ApprovalEngine
from waywarden.tools.model import ToolProvider

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ApprovalHook:
    """Hooks tool invocations through the approval gate.

    Parameters
    ----------
    engine:
        ApprovalEngine instance for persisting requests and decisions.
    registry_providers:
        The list of ToolProvider instances used to derive capabilities.
    tool_policy:
        The ToolPolicy preset dictating auto-allow vs approval-required.
    """

    engine: ApprovalEngine
    registry_providers: list[ToolProvider]
    tool_policy: ToolPolicy

    def requirements(self, tool_id: str, action: str) -> tuple[bool, str | None, str | None]:
        """Return (approval_required, reason, action_reason)."""
        for rule in self.tool_policy.rules:
            if rule.tool != tool_id:
                continue
            if rule.action is not None and rule.action != action:
                continue
            if rule.decision == "auto-allow":
                return False, None, None
            if rule.decision == "forbidden":
                raise RuntimeError(f"tool {tool_id}:{action} forbidden by policy")
            # approval-required
            return True, rule.reason, rule.reason
        if self.tool_policy.default_decision == "auto-allow":
            return False, None, None
        if self.tool_policy.default_decision == "forbidden":
            raise RuntimeError(f"tool {tool_id}:{action} forbidden by policy")
        return True, None, None


class ApprovalGateError(RuntimeError):
    """Raised when an operator blocks an approval."""

    def __init__(self, approval_id: str, reason: str) -> None:
        self.approval_id = approval_id
        self.reason = reason
        super().__init__(f"approval {approval_id} denied: {reason}")
