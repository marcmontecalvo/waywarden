"""Policy domain schema — Pydantic models for policy presets.

Mirrors RT-001 §tool_policy and bridges the YAML boundary into the
domain ``ToolPolicy`` dataclass.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from waywarden.domain.manifest.tool_policy import (
    ToolDecision,
    ToolDecisionRule,
    ToolPolicy,
    ToolPreset,
)


class PolicyPresetDoc(BaseModel, frozen=True):
    """Pydantic model for a single loaded preset YAML."""

    preset: ToolPreset
    default_decision: Literal["auto-allow", "approval-required", "forbidden"] = "approval-required"
    rules: list[ToolDecisionRuleDoc] = Field(default_factory=list)

    def to_domain(self) -> ToolPolicy:
        """Convert to the frozen domain ``ToolPolicy``."""
        return ToolPolicy(
            preset=self.preset,
            default_decision=self.default_decision,
            rules=[
                ToolDecisionRule(
                    tool=r.tool,
                    action=r.action,
                    decision=r.decision,
                    reason=r.reason,
                )
                for r in self.rules
            ],
        )


class ToolDecisionRuleDoc(BaseModel, frozen=True):
    """Single tool-decision rule as parsed from YAML."""

    tool: str
    action: str | None = None
    decision: ToolDecision = "approval-required"
    reason: str | None = None
