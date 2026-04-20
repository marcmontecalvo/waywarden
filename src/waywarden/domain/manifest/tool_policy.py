"""ToolPolicy — tool execution policy for the workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ToolPreset = Literal["yolo", "ask", "allowlist", "custom"]
ToolDecision = Literal["auto-allow", "approval-required", "forbidden"]


@dataclass(frozen=True, slots=True)
class ToolDecisionRule:
    tool: str
    action: str | None = None
    decision: ToolDecision = "approval-required"
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    preset: ToolPreset
    rules: list[ToolDecisionRule]
    default_decision: ToolDecision = "approval-required"
