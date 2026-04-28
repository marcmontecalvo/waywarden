"""Normalized handoff artifacts and correlation metadata for orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from waywarden.domain.ids import DelegationId, RunId


def _clean_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _clean_artifact_ref(value: str) -> str:
    cleaned = _clean_text(value, field_name="artifact_ref")
    if not cleaned.startswith("artifact://"):
        raise ValueError("artifact_ref must use the artifact:// scheme")
    return cleaned


def _clean_run_id(value: RunId | str, *, field_name: str) -> RunId:
    return RunId(_clean_text(str(value), field_name=field_name))


def _clean_optional_run_id(value: RunId | str | None, *, field_name: str) -> RunId | None:
    if value is None:
        return None
    return _clean_run_id(value, field_name=field_name)


def _clean_delegation_id(value: DelegationId | str) -> DelegationId:
    return DelegationId(_clean_text(str(value), field_name="delegation_id"))


@dataclass(frozen=True, slots=True)
class RunCorrelation:
    """Stable run-lineage metadata shared across dispatcher/team/pipeline flows."""

    correlation_id: str
    parent_run_id: RunId | str
    child_run_id: RunId | str
    dispatcher_run_id: RunId | str
    team_run_id: RunId | str
    pipeline_run_id: RunId | str
    delegation_id: DelegationId | str
    manifest_run_id: RunId | str
    sub_agent_run_id: RunId | str | None = None
    review_run_id: RunId | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "correlation_id", _clean_text(self.correlation_id, field_name="correlation_id")
        )
        object.__setattr__(
            self, "parent_run_id", _clean_run_id(self.parent_run_id, field_name="parent_run_id")
        )
        object.__setattr__(
            self, "child_run_id", _clean_run_id(self.child_run_id, field_name="child_run_id")
        )
        object.__setattr__(
            self,
            "dispatcher_run_id",
            _clean_run_id(self.dispatcher_run_id, field_name="dispatcher_run_id"),
        )
        object.__setattr__(
            self, "team_run_id", _clean_run_id(self.team_run_id, field_name="team_run_id")
        )
        object.__setattr__(
            self,
            "pipeline_run_id",
            _clean_run_id(self.pipeline_run_id, field_name="pipeline_run_id"),
        )
        object.__setattr__(self, "delegation_id", _clean_delegation_id(self.delegation_id))
        object.__setattr__(
            self,
            "manifest_run_id",
            _clean_run_id(self.manifest_run_id, field_name="manifest_run_id"),
        )
        object.__setattr__(
            self,
            "sub_agent_run_id",
            _clean_optional_run_id(self.sub_agent_run_id, field_name="sub_agent_run_id"),
        )
        object.__setattr__(
            self,
            "review_run_id",
            _clean_optional_run_id(self.review_run_id, field_name="review_run_id"),
        )

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "correlation_id": self.correlation_id,
            "parent_run_id": str(self.parent_run_id),
            "child_run_id": str(self.child_run_id),
            "dispatcher_run_id": str(self.dispatcher_run_id),
            "team_run_id": str(self.team_run_id),
            "pipeline_run_id": str(self.pipeline_run_id),
            "delegation_id": str(self.delegation_id),
            "manifest_run_id": str(self.manifest_run_id),
        }
        if self.sub_agent_run_id is not None:
            payload["sub_agent_run_id"] = str(self.sub_agent_run_id)
        if self.review_run_id is not None:
            payload["review_run_id"] = str(self.review_run_id)
        return payload


@dataclass(frozen=True, slots=True)
class HandoffArtifact:
    """Normalized handoff artifact shared across dispatcher/team/pipeline flows."""

    artifact_ref: str
    artifact_kind: str
    label: str
    output_name: str
    producer_run_id: RunId | str
    parent_run_id: RunId | str
    child_run_id: RunId | str
    delegation_id: DelegationId | str
    manifest_run_id: RunId | str
    correlation_id: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_ref", _clean_artifact_ref(self.artifact_ref))
        object.__setattr__(
            self, "artifact_kind", _clean_text(self.artifact_kind, field_name="artifact_kind")
        )
        object.__setattr__(self, "label", _clean_text(self.label, field_name="label"))
        object.__setattr__(
            self, "output_name", _clean_text(self.output_name, field_name="output_name")
        )
        object.__setattr__(
            self,
            "producer_run_id",
            _clean_run_id(self.producer_run_id, field_name="producer_run_id"),
        )
        object.__setattr__(
            self, "parent_run_id", _clean_run_id(self.parent_run_id, field_name="parent_run_id")
        )
        object.__setattr__(
            self, "child_run_id", _clean_run_id(self.child_run_id, field_name="child_run_id")
        )
        object.__setattr__(self, "delegation_id", _clean_delegation_id(self.delegation_id))
        object.__setattr__(
            self,
            "manifest_run_id",
            _clean_run_id(self.manifest_run_id, field_name="manifest_run_id"),
        )
        object.__setattr__(
            self, "correlation_id", _clean_text(self.correlation_id, field_name="correlation_id")
        )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
