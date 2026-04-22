"""WorkspaceManifest — the canonical RT-001 workspace manifest model."""

from __future__ import annotations

from dataclasses import dataclass

from waywarden.domain.ids import RunId
from waywarden.domain.manifest.input_mount import InputMount
from waywarden.domain.manifest.network_policy import NetworkPolicy
from waywarden.domain.manifest.output_contract import OutputContract
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import ToolPolicy
from waywarden.domain.manifest.writable_path import WritablePath


@dataclass(frozen=True, slots=True)
class WorkspaceManifest:
    run_id: RunId
    inputs: list[InputMount]
    writable_paths: list[WritablePath]
    outputs: list[OutputContract]
    network_policy: NetworkPolicy
    tool_policy: ToolPolicy
    secret_scope: SecretScope
    snapshot_policy: SnapshotPolicy
