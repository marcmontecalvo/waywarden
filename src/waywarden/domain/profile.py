"""Profile domain models for the core harness.

These types define the profile contract used by the harness core and the
checked-in ``profiles/<id>/profile.yaml`` manifests. They stay pure and
provider-neutral, which aligns with the profile-pack direction in ADR 0001 and
the typed extension contract in ADR 0004.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import NewType

ProfileId = NewType("ProfileId", str)
CURRENT_PROFILE_EXTENSION_EXAMPLES: frozenset[str] = frozenset(
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
PROFILE_EXTENSION_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:-[a-z0-9_]+)*$")


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
    values: tuple[str, ...] | list[str],
) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TypeError("supported_extensions must be a sequence of strings")

    normalized_values: list[str] = []
    seen: set[str] = set()

    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise TypeError(f"supported_extensions[{index}] must be a string")

        normalized = _require_non_empty_text(
            value,
            field_name=f"supported_extensions[{index}]",
        )
        if not PROFILE_EXTENSION_PATTERN.fullmatch(normalized):
            raise ValueError(
                f"supported_extensions[{index}] must be a lowercase extension slug like "
                "'skill' or 'profile_overlay'"
            )
        if normalized in seen:
            raise ValueError(f"supported_extensions[{index}] duplicates {normalized!r}")

        seen.add(normalized)
        normalized_values.append(normalized)

    if not normalized_values:
        raise ValueError("supported_extensions must contain at least one extension")

    return tuple(normalized_values)


@dataclass(frozen=True, slots=True)
class ProfileDescriptor:
    """Describes one profile pack and its supported extension classes."""

    id: ProfileId
    display_name: str
    version: str
    supported_extensions: tuple[str, ...]

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


@dataclass(frozen=True, slots=True, init=False)
class ProfileRegistry(Mapping[ProfileId, ProfileDescriptor]):
    """Read-only lookup of profile descriptors keyed by profile id."""

    _descriptors: Mapping[ProfileId, ProfileDescriptor]

    def __init__(
        self,
        descriptors: Mapping[ProfileId, ProfileDescriptor]
        | Mapping[str, ProfileDescriptor]
        | None = None,
    ) -> None:
        normalized_descriptors: dict[ProfileId, ProfileDescriptor] = {}

        for raw_key, descriptor in (descriptors or {}).items():
            if not isinstance(descriptor, ProfileDescriptor):
                raise TypeError("registry descriptors must be ProfileDescriptor instances")

            key = _normalize_profile_id(raw_key, field_name="profile registry key")
            if descriptor.id != key:
                raise ValueError(
                    f"profile registry key must match descriptor.id ({key!r} != {descriptor.id!r})"
                )
            if key in normalized_descriptors:
                raise ValueError(f"profile registry key {key!r} is duplicated")

            normalized_descriptors[key] = descriptor

        object.__setattr__(
            self,
            "_descriptors",
            MappingProxyType(normalized_descriptors),
        )

    def __getitem__(self, key: ProfileId | str) -> ProfileDescriptor:
        normalized_key = _normalize_profile_id(key, field_name="profile registry lookup")
        return self._descriptors[normalized_key]

    def __iter__(self) -> Iterator[ProfileId]:
        return iter(self._descriptors)

    def __len__(self) -> int:
        return len(self._descriptors)

    def list(self) -> tuple[ProfileDescriptor, ...]:
        """Return all registered descriptors in deterministic (id-sorted) order."""
        return tuple(self._descriptors.values())
