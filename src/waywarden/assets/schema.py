"""Canonical metadata schema for shared assets.

Every shared asset under ``assets/<kind>/<id>/`` carries a metadata
record described by ``AssetMetadata`` (Pydantic v2).  Kind-specific
sub-classes attach kind-level fields on top of the common base.

This schema is the single authority for asset identification, version
coercion, and profile-filter hints.  Loaders that read ``asset.yaml``
must validate through these models and raise on any schema violation —
silent coercion is explicitly forbidden.

Canonical references:
    - ADR 0002 (core + profile packs)
    - ADR 0004 (extension contract)
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Asset kind enumeration
# ---------------------------------------------------------------------------

AssetKind = Literal[
    "routine",
    "widget",
    "command",
    "prompt",
    "tool",
    "skill",
    "agent",
    "team",
    "pipeline",
    "policy",
    "theme",
    "context_provider",
    "profile_overlay",
]

KNOWN_ASSET_KINDS: frozenset[AssetKind] = frozenset(
    [
        "routine",
        "widget",
        "command",
        "prompt",
        "tool",
        "skill",
        "agent",
        "team",
        "pipeline",
        "policy",
        "theme",
        "context_provider",
        "profile_overlay",
    ]
)

# ---------------------------------------------------------------------------
# Auxiliary types
# ---------------------------------------------------------------------------

_PROFILE_FILTER_OP = Literal["include", "exclude"]

# Semver regex pattern for version coercion.
SEMVER_RE = (
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class AssetValidationError(ValueError):
    """Raised when asset metadata fails validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(self.__str__())

    def __str__(self) -> str:
        lines = ["Asset validation failed:"]
        lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core metadata model
# ---------------------------------------------------------------------------


class AssetMetadata(BaseModel, frozen=True, extra="forbid"):
    """Common metadata shared by every asset kind.

    Required fields:
        - ``id``: unique asset identifier (slug-like).
        - ``kind``: one of the known ``AssetKind`` values.
        - ``version``: semver string, coerced to ``X.Y.Z`` form.
        - ``description``: human-readable description.
        - ``tags``: optional label set for profile-filter hints.
        - ``required_providers``: optional list of provider names this
          asset needs to function.
        - ``profile_filter``: optional profile-filter hints that gate
          which profiles receive this asset.
    """

    id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[a-z][a-z0-9_-]*$",
    )
    kind: AssetKind
    version: str = Field(
        min_length=5,
        max_length=64,
    )
    description: str = Field(
        min_length=1,
        max_length=4096,
    )
    tags: tuple[str, ...] = ()
    required_providers: tuple[str, ...] = ()
    profile_filter: tuple[dict[str, Any], ...] = ()

    @field_validator("id", mode="before")
    @classmethod
    def _normalize_id(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("id must be a string")
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("id must not be blank")
        return normalized

    @field_validator("kind", mode="before")
    @classmethod
    def _normalize_kind(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("kind must be a string")
        normalized = value.strip().lower()
        if normalized not in KNOWN_ASSET_KINDS:
            raise ValueError(f"kind must be one of {sorted(KNOWN_ASSET_KINDS)}, got {value!r}")
        return normalized

    @field_validator("version", mode="before")
    @classmethod
    def _coerce_version(cls, value: object) -> str:
        """Coerce version values to strict ``X.Y.Z`` semver form.

        Accepts numeric versions like ``1`` or ``1.2``, and normalises
        them to ``1.0.0`` / ``1.2.0``.  Full semver strings pass
        through unchanged (modulo stripping).
        """
        if not isinstance(value, str):
            raise TypeError("version must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("version must not be blank")
        parts = normalized.split(".")
        if all(p.isdigit() for p in parts) and len(parts) <= 3:
            padded = parts + ["0"] * (3 - len(parts))
            return ".".join(padded)
        return normalized

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise TypeError("tags must be a string or sequence of strings")
        result: list[str] = []
        seen: set[str] = set()
        for idx, item in enumerate(value):
            if not isinstance(item, str):
                raise TypeError(f"tags[{idx}] must be a string")
            trimmed = item.strip()
            if not trimmed:
                continue
            if trimmed not in seen:
                seen.add(trimmed)
                result.append(trimmed)
        return tuple(result)

    @field_validator("required_providers", mode="before")
    @classmethod
    def _normalize_required_providers(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise TypeError("required_providers must be a string or sequence of strings")
        result: list[str] = []
        for idx, item in enumerate(value):
            if not isinstance(item, str):
                raise TypeError(f"required_providers[{idx}] must be a string")
            trimmed = item.strip().lower()
            if not trimmed:
                continue
            result.append(trimmed)
        return tuple(dict.fromkeys(result))

    @field_validator("profile_filter", mode="before")
    @classmethod
    def _normalize_profile_filter(cls, value: object) -> tuple[dict[str, Any], ...]:
        if not isinstance(value, (list, tuple)):
            if value is None:
                return ()
            raise TypeError("profile_filter must be a sequence or null")
        result: list[dict[str, Any]] = []
        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                raise TypeError(f"profile_filter[{idx}] must be a mapping")
            for key in item:
                if not isinstance(key, str):
                    raise TypeError(f"profile_filter[{idx}] key must be a string")
            result.append(dict(item))
        return tuple(result)

    @model_validator(mode="after")
    def _validate_profile_filter_ops(self) -> AssetMetadata:
        """Ensure profile_filter entries carry an ``op`` field."""
        valid_ops: frozenset[str] = frozenset({"include", "exclude"})
        for idx, entry in enumerate(self.profile_filter):
            if "op" not in entry:
                raise ValueError(
                    f"profile_filter[{idx}] missing required 'op' field "
                    f"(one of {sorted(valid_ops)})"
                )
            if entry["op"] not in valid_ops:
                raise ValueError(
                    f"profile_filter[{idx}].op must be one of "
                    f"{sorted(valid_ops)}, got {entry['op']!r}"
                )
        return self

    def to_json_schema(self) -> dict[str, Any]:
        """Return a JSON Schema (Draft 2020-12) representation."""
        return self.model_json_schema(
            by_alias=True,
            ref_template="#/definitions/{model}",
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable dict representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssetMetadata:
        """Validate and construct from a plain dict (for YAML loading).

        Raises ``AssetValidationError`` when any field fails validation.
        """
        errors: list[str] = []
        try:
            model_cls: type[AssetMetadata] = _asset_model_for_kind(data.get("kind"))
            return model_cls(**data)
        except Exception as exc:
            if hasattr(exc, "errors"):
                for err in exc.errors():
                    field = ".".join(str(part) for part in err.get("loc", []))
                    msg = err.get("msg", str(exc))
                    errors.append(f"{field}: {msg}")
            else:
                errors.append(str(exc))
            raise AssetValidationError(errors) from exc


# ---------------------------------------------------------------------------
# Kind-specific metadata (extensibility)
# ---------------------------------------------------------------------------


class RoutineMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``routine`` kind.

    Additional fields capture the routine's orchestration contract.
    """

    kind: Literal["routine"] = "routine"
    milestones: tuple[dict[str, Any], ...] = ()
    emits_events: tuple[str, ...] = ()

    @field_validator("milestones", mode="before")
    @classmethod
    def _normalize_milestones(cls, value: object) -> tuple[dict[str, Any], ...]:
        if value is None:
            return ()
        if not isinstance(value, (list, tuple)):
            raise TypeError("milestones must be a sequence of mappings")
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise TypeError(f"milestones[{index}] must be a mapping")
            normalized.append(dict(item))
        return tuple(normalized)


class WidgetMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``widget`` kind."""

    kind: Literal["widget"] = "widget"
    ui_surface: str = ""
    component_id: str = ""


class CommandMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``command`` kind."""

    kind: Literal["command"] = "command"
    trigger: str = ""
    aliases: tuple[str, ...] = ()


class PromptMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``prompt`` kind."""

    kind: Literal["prompt"] = "prompt"
    template_format: Literal["jinja2", "mustache", "plain"] = "plain"
    system_message: str = ""


class ToolMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``tool`` kind."""

    kind: Literal["tool"] = "tool"
    function_name: str = ""
    parameters_schema: dict[str, Any] = {}


class SkillMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``skill`` kind."""

    kind: Literal["skill"] = "skill"
    trigger_patterns: tuple[str, ...] = ()


class AgentMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``agent`` kind."""

    kind: Literal["agent"] = "agent"
    role: str = ""
    max_tools_per_step: int = Field(ge=1)


class TeamMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``team`` kind."""

    kind: Literal["team"] = "team"
    members: tuple[str, ...] = ()
    coordinator: str = ""


class PipelineMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``pipeline`` kind."""

    kind: Literal["pipeline"] = "pipeline"
    stages: tuple[str, ...] = ()
    timeout_seconds: int = 0


class PolicyMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``policy`` kind."""

    kind: Literal["policy"] = "policy"
    enforce_mode: Literal["allow", "block", "audit"] = "block"
    preset: str = ""


class ThemeMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``theme`` kind."""

    kind: Literal["theme"] = "theme"
    palette: tuple[str, ...] = ()
    font_family: str = ""


class ContextProviderMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``context_provider`` kind."""

    kind: Literal["context_provider"] = "context_provider"
    inject_keys: tuple[str, ...] = ()


class ProfileOverlayMetadata(AssetMetadata, frozen=True):
    """Asset metadata for ``profile_overlay`` kind."""

    kind: Literal["profile_overlay"] = "profile_overlay"
    target_profiles: tuple[str, ...] = ()


_ASSET_MODEL_BY_KIND: dict[str, type[AssetMetadata]] = {
    "routine": RoutineMetadata,
    "widget": WidgetMetadata,
    "command": CommandMetadata,
    "prompt": PromptMetadata,
    "tool": ToolMetadata,
    "skill": SkillMetadata,
    "agent": AgentMetadata,
    "team": TeamMetadata,
    "pipeline": PipelineMetadata,
    "policy": PolicyMetadata,
    "theme": ThemeMetadata,
    "context_provider": ContextProviderMetadata,
    "profile_overlay": ProfileOverlayMetadata,
}


def _asset_model_for_kind(kind: object) -> type[AssetMetadata]:
    if not isinstance(kind, str):
        return AssetMetadata
    return _ASSET_MODEL_BY_KIND.get(kind.strip().lower(), AssetMetadata)


# ---------------------------------------------------------------------------
# Cross-asset validation helpers
# ---------------------------------------------------------------------------


def validate_unique_ids(
    assets: list[AssetMetadata],
) -> list[str]:
    """Return duplicate-id errors when the same ``id`` appears across
    multiple assets (even across different kinds).

    This enforces the "declare once, reference by id" contract from
    ADR 0002 and ADR 0004.
    """
    seen: dict[str, list[AssetMetadata]] = {}
    for asset in assets:
        seen.setdefault(asset.id, []).append(asset)

    errors: list[str] = []
    for aid, entries in sorted(seen.items()):
        if len(entries) > 1:
            kinds = sorted(set(e.kind for e in entries))
            errors.append(f"asset id {aid!r} is declared in {len(entries)} assets (kinds: {kinds})")
    return errors
