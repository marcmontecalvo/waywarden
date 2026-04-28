"""Provider-neutral metadata seams for P8 durability handoff.

These value types are metadata only. They classify side effects and surface
token budget context for future schedulers, leases, DLQs, escrow, and saga
rollback without implementing those P8 behaviors in P7 code.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

SideEffectClass = Literal[
    "read-only",
    "workspace-mutating",
    "DB-mutating",
    "provider-mutating",
    "external-write",
    "unknown/high-risk",
]

_SIDE_EFFECT_CLASSES: frozenset[str] = frozenset(
    {
        "read-only",
        "workspace-mutating",
        "DB-mutating",
        "provider-mutating",
        "external-write",
        "unknown/high-risk",
    }
)


def _clean_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _validate_non_negative(value: int | None, *, field_name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise TypeError(f"{field_name} must be an int or None")
    if value < 0:
        raise ValueError("token counts must be non-negative")
    return value


@dataclass(frozen=True, slots=True)
class SideEffectClassification:
    """Classify a tool action's durable side-effect risk."""

    action_class: SideEffectClass | str
    rationale: str

    def __post_init__(self) -> None:
        action_class = _clean_text(self.action_class, field_name="action_class")
        if action_class not in _SIDE_EFFECT_CLASSES:
            raise ValueError("action_class must be a supported side-effect class")
        object.__setattr__(self, "action_class", action_class)
        object.__setattr__(self, "rationale", _clean_text(self.rationale, field_name="rationale"))

    def as_payload(self) -> dict[str, object]:
        return {
            "action_class": self.action_class,
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class ToolActionMetadata:
    """Metadata for a tool call/action visible to durability and rollback code."""

    tool_id: str
    action: str
    side_effect: SideEffectClassification
    approval_explanation: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_id", _clean_text(self.tool_id, field_name="tool_id"))
        object.__setattr__(self, "action", _clean_text(self.action, field_name="action"))
        if not isinstance(self.side_effect, SideEffectClassification):
            raise TypeError("side_effect must be a SideEffectClassification")
        object.__setattr__(
            self,
            "approval_explanation",
            MappingProxyType(dict(self.approval_explanation)),
        )

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "tool_id": self.tool_id,
            "action": self.action,
            "side_effect": self.side_effect.as_payload(),
        }
        if self.approval_explanation:
            payload["approval_explanation"] = dict(self.approval_explanation)
        return payload


@dataclass(frozen=True, slots=True)
class TokenBudgetTelemetry:
    """Optional token budget context supplied by callers.

    This does not enforce budgets, escrow tokens, downgrade models, or trigger
    wrap-up behavior. It only makes the caller's budget metadata visible.
    """

    source: str
    budget_id: str | None = None
    observed_prompt_tokens: int | None = None
    observed_completion_tokens: int | None = None
    observed_total_tokens: int | None = None
    remaining_tokens: int | None = None
    warning: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _clean_text(self.source, field_name="source"))
        if self.budget_id is not None:
            object.__setattr__(
                self, "budget_id", _clean_text(self.budget_id, field_name="budget_id")
            )
        if self.warning is not None:
            object.__setattr__(self, "warning", _clean_text(self.warning, field_name="warning"))
        for field_name in (
            "observed_prompt_tokens",
            "observed_completion_tokens",
            "observed_total_tokens",
            "remaining_tokens",
        ):
            object.__setattr__(
                self,
                field_name,
                _validate_non_negative(getattr(self, field_name), field_name=field_name),
            )

    def as_payload(self) -> dict[str, object]:
        return {
            "budget_id": self.budget_id,
            "source": self.source,
            "observed_prompt_tokens": self.observed_prompt_tokens,
            "observed_completion_tokens": self.observed_completion_tokens,
            "observed_total_tokens": self.observed_total_tokens,
            "remaining_tokens": self.remaining_tokens,
            "warning": self.warning,
        }


def token_budget_payload(token_budget: TokenBudgetTelemetry | None) -> dict[str, object] | None:
    if token_budget is None:
        return None
    if not isinstance(token_budget, TokenBudgetTelemetry):
        raise TypeError("token_budget must be a TokenBudgetTelemetry")
    return token_budget.as_payload()


def tool_actions_payload(
    tool_actions: tuple[ToolActionMetadata, ...] | None,
) -> tuple[dict[str, object], ...] | None:
    if tool_actions is None:
        return None
    actions = tuple(tool_actions)
    for action in actions:
        if not isinstance(action, ToolActionMetadata):
            raise TypeError("tool_actions must contain ToolActionMetadata values")
    return tuple(action.as_payload() for action in actions)


__all__ = [
    "SideEffectClass",
    "SideEffectClassification",
    "TokenBudgetTelemetry",
    "ToolActionMetadata",
    "token_budget_payload",
    "tool_actions_payload",
]
