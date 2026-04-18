"""Instance domain models for the core harness.

These types keep instance identity and overlay configuration in the domain
layer, which matches the API-first and multi-instance direction in ADR 0001.
They stay intentionally provider-neutral and import no framework code.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, NewType, TypedDict

InstanceId = NewType("InstanceId", str)


class InstanceManifest(TypedDict):
    """Typed shape for entries in ``config/instances.yaml``."""

    id: str
    display_name: str
    profile_id: str
    config_path: str


def _require_non_empty_text(value: str, *, field_name: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{field_name} must not be blank")
    return trimmed


def _normalize_instance_id(value: str | InstanceId, *, field_name: str) -> InstanceId:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = _require_non_empty_text(value, field_name=field_name)
    return InstanceId(normalized)


@dataclass(frozen=True, slots=True)
class InstanceDescriptor:
    """Describes one named instance of a profile pack."""

    id: InstanceId
    display_name: str
    profile_id: str
    config_path: Path

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            _normalize_instance_id(self.id, field_name="id"),
        )
        object.__setattr__(
            self,
            "display_name",
            _require_non_empty_text(self.display_name, field_name="display_name"),
        )
        object.__setattr__(
            self,
            "profile_id",
            _require_non_empty_text(self.profile_id, field_name="profile_id"),
        )

        if isinstance(self.config_path, Path):
            config_path = self.config_path
        elif isinstance(self.config_path, str):
            config_path = Path(_require_non_empty_text(self.config_path, field_name="config_path"))
        else:
            raise TypeError("config_path must be a path-like string or Path")

        if str(config_path).strip() == "":
            raise ValueError("config_path must not be blank")

        object.__setattr__(self, "config_path", config_path)


@dataclass(frozen=True, slots=True)
class InstanceConfig:
    """Runtime overlay for an instance without binding to any provider shape."""

    env: Mapping[str, str] = field(default_factory=dict)
    overrides: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_env: dict[str, str] = {}
        for key, value in self.env.items():
            normalized_key = _require_non_empty_text(key, field_name="env key")
            if not isinstance(value, str):
                raise TypeError(f"env[{normalized_key!r}] must be a string")
            normalized_env[normalized_key] = value

        object.__setattr__(self, "env", normalized_env)
        object.__setattr__(self, "overrides", dict(self.overrides))


@dataclass(frozen=True, slots=True, init=False)
class InstanceRegistry(Mapping[InstanceId, InstanceDescriptor]):
    """Read-only lookup of instance descriptors keyed by instance id."""

    _descriptors: Mapping[InstanceId, InstanceDescriptor]

    def __init__(
        self,
        descriptors: Mapping[InstanceId, InstanceDescriptor]
        | Mapping[str, InstanceDescriptor]
        | None = None,
    ) -> None:
        normalized_descriptors: dict[InstanceId, InstanceDescriptor] = {}

        for raw_key, descriptor in (descriptors or {}).items():
            if not isinstance(descriptor, InstanceDescriptor):
                raise TypeError("registry descriptors must be InstanceDescriptor instances")

            key = _normalize_instance_id(raw_key, field_name="instance registry key")
            if descriptor.id != key:
                raise ValueError(
                    f"instance registry key must match descriptor.id ({key!r} != {descriptor.id!r})"
                )
            if key in normalized_descriptors:
                raise ValueError(f"instance registry key {key!r} is duplicated")

            normalized_descriptors[key] = descriptor

        object.__setattr__(
            self,
            "_descriptors",
            MappingProxyType(normalized_descriptors),
        )

    def __getitem__(self, key: InstanceId | str) -> InstanceDescriptor:
        normalized_key = _normalize_instance_id(key, field_name="instance registry lookup")
        return self._descriptors[normalized_key]

    def __iter__(self) -> Iterator[InstanceId]:
        return iter(self._descriptors)

    def __len__(self) -> int:
        return len(self._descriptors)
