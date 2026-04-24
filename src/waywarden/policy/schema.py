<<<<<<< HEAD
"""Pydantic v2 schema for policy-preset YAML deserialization.

Mirrors the RT-001 ``tool_policy`` surface so that a YAML preset can
be validated against a pydantic model before converting into the
frozen domain ``ToolPolicy``.
=======
"""Policy domain schema — Pydantic models for policy presets.

Mirrors RT-001 §tool_policy and bridges the YAML boundary into the
domain ``ToolPolicy`` dataclass.
>>>>>>> 7c5089dabbd83f11c39650e78b76e58c185e571e
"""

from __future__ import annotations

from typing import Literal

<<<<<<< HEAD
from pydantic import BaseModel, ConfigDict, Field

ToolPreset = Literal["yolo", "ask", "allowlist", "custom"]
ToolDecision = Literal["auto-allow", "approval-required", "forbidden"]


class ToolDecisionRule(BaseModel):
    """Single rule inside a policy preset."""

    model_config = ConfigDict(frozen=True, slots=True)

    tool: str
    action: str | None = None
    decision: ToolDecision = Field(default="approval-required")
    reason: str | None = None


class PolicyPresetDoc(BaseModel):
    """Top-level schema for a policy-preset YAML document.

    The ``preset`` field is one of the four canonical values from
    ADR-0005: ``yolo``, ``ask``, ``allowlist``, ``custom``.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    preset: ToolPreset
    default_decision: ToolDecision = Field(default="approval-required")
    rules: list[ToolDecisionRule] = Field(default_factory=list)
=======
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
>>>>>>> 7c5089dabbd83f11c39650e78b76e58c185e571e
