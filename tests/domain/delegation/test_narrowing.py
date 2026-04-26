"""Unit tests for narrowing_manifest — valid narrowing per field."""

from __future__ import annotations

import pytest

from waywarden.domain.delegation.narrowing import (
    DelegationWideningError,
    narrow_manifest,
)
from waywarden.domain.ids import RunId
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.manifest.network_policy import NetworkAllowRule, NetworkPolicy
from waywarden.domain.manifest.output_contract import OutputContract
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import (
    ToolPolicy,
)
from waywarden.domain.manifest.writable_path import WritablePath


def _base_manifest(
    writable_paths: list[WritablePath] | None = None,
    network_policy: NetworkPolicy | None = None,
    tool_policy: ToolPolicy | None = None,
    secret_scope: SecretScope | None = None,
) -> WorkspaceManifest:
    wp = writable_paths or [WritablePath(path="/tmp", purpose="task-scratch")]
    np = network_policy or NetworkPolicy(mode="allowlist", allow=[], deny=[])
    tp = tool_policy or ToolPolicy(preset="ask", rules=[], default_decision="approval-required")
    ss = secret_scope or SecretScope(
        mode="brokered",
        allowed_secret_refs=["ref-a"],
        mount_env=["SECRET_A"],
        redaction_level="full",
    )
    return WorkspaceManifest(
        run_id=RunId("run-parent"),
        inputs=[],
        writable_paths=wp,
        outputs=[OutputContract(name="summary", path="/tmp/summary", kind="text", required=True)],
        network_policy=np,
        tool_policy=tp,
        secret_scope=ss,
        snapshot_policy=SnapshotPolicy(
            on_start=False,
            on_completion=False,
            on_failure=False,
            before_destructive_actions=True,
            max_snapshots=10,
            include_paths=[],
            exclude_paths=[],
        ),
    )


def _child_manifest(
    writable_paths: list[WritablePath] | None = None,
    network_policy: NetworkPolicy | None = None,
    tool_policy: ToolPolicy | None = None,
    secret_scope: SecretScope | None = None,
) -> WorkspaceManifest:
    return _base_manifest(
        writable_paths=writable_paths,
        network_policy=network_policy,
        tool_policy=tool_policy,
        secret_scope=secret_scope,
    )


# ---------------------------------------------------------------------------
# Passing narrowing validations
# ---------------------------------------------------------------------------


def test_writable_paths_narrowing() -> None:
    """Child with fewer writable paths passes."""
    parent = _base_manifest(
        writable_paths=[
            WritablePath(path="/tmp", purpose="task-scratch"),
            WritablePath(path="/var/log", purpose="cache"),
        ]
    )
    child = _child_manifest(
        writable_paths=[WritablePath(path="/tmp", purpose="task-scratch")],
    )
    # Should not raise
    narrow_manifest(parent, child)


def test_network_policy_narrowing() -> None:
    """Child denying more hosts passes; child adding hosts to allowlist fails."""
    parent_network = NetworkPolicy(
        mode="allowlist",
        allow=[NetworkAllowRule(host_pattern="internal.local", purpose="db", port=5432)],
        deny=["extern.example.com"],
    )
    child_network = NetworkPolicy(
        mode="allowlist",
        allow=[NetworkAllowRule(host_pattern="internal.local", purpose="db", port=5432)],
        deny=["extern.example.com", "bad.actor.io"],
    )
    parent = _base_manifest(network_policy=parent_network)
    child = _child_manifest(network_policy=child_network)

    # More deny rules only — should pass
    narrow_manifest(parent, child)

    # Child adding a NEW allow host should fail
    child_wide_network = NetworkPolicy(
        mode="allowlist",
        allow=[
            NetworkAllowRule(host_pattern="internal.local", purpose="db", port=5432),
            NetworkAllowRule(host_pattern="new.external.com", purpose="external", port=443),
        ],
        deny=["extern.example.com"],
    )
    child_wide = _child_manifest(network_policy=child_wide_network)
    with pytest.raises(DelegationWideningError) as exc_info:
        narrow_manifest(parent, child_wide)
    assert exc_info.value.field == "network_policy"


def test_tool_policy_narrowing() -> None:
    """Child with more restrictive tool preset passes."""
    parent_tool = ToolPolicy(
        preset="yolo",
        rules=[],
        default_decision="auto-allow",
    )
    child_tool = ToolPolicy(
        preset="ask",
        rules=[],
        default_decision="approval-required",
    )
    parent = _base_manifest(tool_policy=parent_tool)
    child = _child_manifest(tool_policy=child_tool)
    # ask is narrower than yolo
    narrow_manifest(parent, child)


def test_secret_scope_narrowing() -> None:
    """Child with fewer allowed secret refs passes."""
    parent_secret = SecretScope(
        mode="brokered",
        allowed_secret_refs=["ref-a", "ref-b", "ref-c"],
        mount_env=["SECRET_A", "SECRET_B", "SECRET_C"],
        redaction_level="full",
    )
    child_secret = SecretScope(
        mode="brokered",
        allowed_secret_refs=["ref-a"],
        mount_env=["SECRET_A"],
        redaction_level="full",
    )
    parent = _base_manifest(secret_scope=parent_secret)
    child = _child_manifest(secret_scope=child_secret)
    narrow_manifest(parent, child)


# ---------------------------------------------------------------------------
# Widening validations
# ---------------------------------------------------------------------------


def test_widening_raises() -> None:
    """Widening any guarded field raises DelegationWideningError naming the field."""
    # writable_paths widening
    parent = _base_manifest(
        writable_paths=[WritablePath(path="/tmp", purpose="task-scratch")],
    )
    child = _child_manifest(
        writable_paths=[
            WritablePath(path="/tmp", purpose="task-scratch"),
            WritablePath(path="/new/path", purpose="declared-output"),
        ],
    )
    with pytest.raises(DelegationWideningError) as exc_info:
        narrow_manifest(parent, child)
    assert exc_info.value.field == "writable_paths"
