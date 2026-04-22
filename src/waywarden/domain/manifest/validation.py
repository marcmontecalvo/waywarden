"""Validation rules for WorkspaceManifest per RT-001."""

from __future__ import annotations

import os
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from waywarden.domain.manifest.manifest import WorkspaceManifest

if TYPE_CHECKING:
    from waywarden.domain.manifest.writable_path import WritablePath


def _is_absolute_normalized(path: str) -> bool:
    """Return True if *path* is absolute and normalized."""
    return path.startswith("/") and path == os.path.normpath(path)


def _validate_manifest(manifest: WorkspaceManifest) -> None:
    """Run all RT-001 validation rules on *manifest*.

    Raises ``ValueError`` when any rule is violated.
    """
    for inp in manifest.inputs:
        if not _is_absolute_normalized(inp.target_path):
            raise ValueError(
                f"input target_path must be absolute and normalized: {inp.target_path!r}"
            )

    for wp in manifest.writable_paths:
        if not _is_absolute_normalized(wp.path):
            raise ValueError(f"writable_path must be absolute and normalized: {wp.path!r}")

    for out in manifest.outputs:
        if not _is_absolute_normalized(out.path):
            raise ValueError(f"output path must be absolute and normalized: {out.path!r}")

    _seen_targets: set[str] = set()
    for inp in manifest.inputs:
        if inp.target_path in _seen_targets:
            raise ValueError(f"duplicate input target_path: {inp.target_path!r}")
        _seen_targets.add(inp.target_path)

    for out in manifest.outputs:
        if not _is_inside_any(out.path, manifest.writable_paths):
            raise ValueError(f"output path {out.path!r} is not inside any writable_path")

    if manifest.network_policy.mode == "allowlist" and not manifest.network_policy.allow:
        raise ValueError(
            "network_policy mode 'allowlist' with empty allow list is ambiguous; "
            "use 'deny' mode instead"
        )

    if manifest.network_policy.mode == "profile-default":
        raise ValueError(
            "network_policy mode 'profile-default' must be normalized to a "
            "concrete mode before construction"
        )

    _validate_writable_overlaps(manifest.writable_paths)


def _is_inside_any(path: str, writable_paths: list[WritablePath]) -> bool:
    """Return True if *path* is inside or equal to at least one writable path."""
    p = PurePosixPath(path)
    for wp in writable_paths:
        wp_path = PurePosixPath(wp.path)
        try:
            p.relative_to(wp_path)
            return True
        except ValueError:
            continue
    return False


def _validate_writable_overlaps(writable_paths: list[WritablePath]) -> None:
    """Validate writable path overlap rules."""
    for i, wp_a in enumerate(writable_paths):
        for j, wp_b in enumerate(writable_paths):
            if i >= j:
                continue
            path_a = PurePosixPath(wp_a.path)
            path_b = PurePosixPath(wp_b.path)
            try:
                path_b.relative_to(path_a)
                if _identical_grant(wp_a, wp_b):
                    continue
                raise ValueError(
                    f"writable paths {wp_a.path!r} and {wp_b.path!r} overlap "
                    "with different grants — ambiguous"
                )
            except ValueError:
                try:
                    path_a.relative_to(path_b)
                    if _identical_grant(wp_b, wp_a):
                        continue
                    raise ValueError(
                        f"writable paths {wp_a.path!r} and {wp_b.path!r} overlap "
                        "with different grants — ambiguous"
                    )
                except ValueError:
                    continue


def _identical_grant(wp_a: WritablePath, wp_b: WritablePath) -> bool:
    """Return True if two writable paths have identical grant attributes."""
    return (
        wp_a.purpose == wp_b.purpose
        and wp_a.max_size_mb == wp_b.max_size_mb
        and wp_a.retention == wp_b.retention
    )
