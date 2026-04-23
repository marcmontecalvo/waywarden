"""Pydantic v2 schema for policy-preset YAML deserialization.

Mirrors the RT-001 ``tool_policy`` surface so that a YAML preset can
be validated against a pydantic model before converting into the
frozen domain ``ToolPolicy``.
"""

from __future__ import annotations

from typing import Literal

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
