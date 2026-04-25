"""Delegation widening validation.

RT-001 §Delegated task attachment: the child manifest must be a **strict
narrowing** of the parent on every guarded field.  Any attempt to widen
authority raises ``DelegationWideningError``.

Guarded fields:
- ``writable_paths`` — child may not add new paths
- ``network_policy`` — child may deny more, allow less
- ``tool_policy`` — child may restrict tools further
- ``secret_scope`` — child may expose fewer secrets
"""

from __future__ import annotations

from waywarden.domain.manifest.manifest import WorkspaceManifest


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class DelegationWideningError(RuntimeError):
    """Raised when a child manifest widens authority relative to the parent.

    Attributes
    ----------
    field:
        The specific field that expanded (e.g. ``"writable_paths"``).
    """

    def __init__(self, field: str) -> None:
        super().__init__(
            f"child manifest widens authority on {field!r} — "
            "narrowing validation required"
        )
        self.field = field


# ---------------------------------------------------------------------------
# Narrowing validation
# ---------------------------------------------------------------------------


def narrow_manifest(
    parent: WorkspaceManifest,
    child: WorkspaceManifest,
) -> None:
    """Validate that *child* is a strict narrowing of *parent*.

    Mutually exclusive: this function **asserts** correctness.
    It does NOT modify either manifest.

    Parameters
    ----------
    parent:
        The parent (wider) manifest.
    child:
        The child (narrower) manifest to validate.

    Raises
    ------
    DelegationWideningError:
        If any guarded field is widened in the child relative to the parent.
    """
    _narrow_writable_paths(parent, child)
    _narrow_network_policy(parent, child)
    _narrow_tool_policy(parent, child)
    _narrow_secret_scope(parent, child)


# ---------------------------------------------------------------------------
# Private validators
# ---------------------------------------------------------------------------


def _narrow_writable_paths(parent: WorkspaceManifest, child: WorkspaceManifest) -> None:
    child_paths = {p.path for p in child.writable_paths}
    parent_paths = {p.path for p in parent.writable_paths}
    extra = child_paths - parent_paths
    if extra:
        raise DelegationWideningError("writable_paths")


def _narrow_network_policy(parent: WorkspaceManifest, child: WorkspaceManifest) -> None:
    """Child may deny more hosts, but may not add new allow rules beyond the parent."""
    # If the parent has allowlist mode, child may only reference existing hosts
    if parent.network_policy.mode == "allowlist":
        parent_allow = {r.host_pattern for r in parent.network_policy.allow}
        child_allow = {r.host_pattern for r in child.network_policy.allow}
        new_allow = child_allow - parent_allow
        if new_allow:
            raise DelegationWideningError("network_policy")


def _narrow_tool_policy(parent: WorkspaceManifest, child: WorkspaceManifest) -> None:
    """Child may not make tools less restricted (e.g. allowlist → yolo)."""
    _preset_order = {"yolo": 3, "ask": 2, "allowlist": 1, "custom": 0}
    parent_preset = parent.tool_policy.preset
    child_preset = child.tool_policy.preset
    parent_level = _preset_order[parent_preset]
    child_level = _preset_order[child_preset]
    if child_level > parent_level:
        raise DelegationWideningError("tool_policy")


def _narrow_secret_scope(parent: WorkspaceManifest, child: WorkspaceManifest) -> None:
    """Child may not expose secrets not already exposed by the parent."""
    parent_allowed = set(parent.secret_scope.allowed_secret_refs)
    child_allowed = set(child.secret_scope.allowed_secret_refs)
    new_secrets = child_allowed - parent_allowed
    if new_secrets:
        raise DelegationWideningError("secret_scope")
