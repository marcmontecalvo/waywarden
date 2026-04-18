"""Profile domain models for the core harness.

These types define the profile contract used by the harness core and the
checked-in ``profiles/<id>/profile.yaml`` manifests. They stay pure and
provider-neutral, which aligns with the profile-pack direction in ADR 0001 and
the typed extension contract in ADR 0004.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, NewType, TypedDict, cast

ProfileId = NewType("ProfileId", str)
ProfileExtension = Literal[
    "widget",
    "command",
    "prompt",
    "tool",
    "skill",
    "agent",
    "team",
    "pipeline",
    "routine",
    "policy",
    "theme",
    "context_provider",
    "profile_overlay",
]

SUPPORTED_PROFILE_EXTENSIONS: frozenset[str] = frozenset(
    {
        "widget",
        "command",
        "prompt",
        "tool",
        "skill",
        "agent",
        "team",
        "pipeline",
        "routine",
        "policy",
        "theme",
        "context_provider",
        "profile_overlay",
    }
)
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class ProfileManifest(TypedDict):
    """Typed shape for ``profiles/<id>/profile.yaml`` documents."""

    id: str
    display_name: str
    version: str
    supported_extensions: list[ProfileExtension]


def _require_non_empty_text(value: str, *, field_name: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{field_name} must not be blank")
    return trimmed


def _normalize_profile_id(value: str | ProfileId, *, field_name: str) -> ProfileId:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = _require_non_empty_text(value, field_name=field_name)
    return ProfileId(normalized)


def _normalize_version(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = _require_non_empty_text(value, field_name=field_name)
    if not SEMVER_PATTERN.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a semantic version like 1.0.0")
    return normalized


def _normalize_supported_extensions(
    values: tuple[ProfileExtension, ...] | list[str],
) -> tuple[ProfileExtension, ...]:
    if isinstance(values, str):
        raise TypeError("supported_extensions must be a sequence of strings")

    normalized_values: list[ProfileExtension] = []
    seen: set[str] = set()

    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise TypeError(f"supported_extensions[{index}] must be a string")

        normalized = _require_non_empty_text(
            value,
            field_name=f"supported_extensions[{index}]",
        )
        if normalized not in SUPPORTED_PROFILE_EXTENSIONS:
            raise ValueError(
                f"supported_extensions[{index}] must be one of "
                f"{sorted(SUPPORTED_PROFILE_EXTENSIONS)!r}"
            )
        if normalized in seen:
            raise ValueError(f"supported_extensions[{index}] duplicates {normalized!r}")

        seen.add(normalized)
        normalized_values.append(cast("ProfileExtension", normalized))

    if not normalized_values:
        raise ValueError("supported_extensions must contain at least one extension")

    return tuple(normalized_values)


@dataclass(frozen=True, slots=True)
class ProfileDescriptor:
    """Describes one profile pack and its supported extension classes."""

    id: ProfileId
    display_name: str
    version: str
    supported_extensions: tuple[ProfileExtension, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            _normalize_profile_id(self.id, field_name="id"),
        )
        object.__setattr__(
            self,
            "display_name",
            _require_non_empty_text(self.display_name, field_name="display_name"),
        )
        object.__setattr__(
            self,
            "version",
            _normalize_version(self.version, field_name="version"),
        )
        object.__setattr__(
            self,
            "supported_extensions",
            _normalize_supported_extensions(list(self.supported_extensions)),
        )

