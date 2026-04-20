"""WorkspaceManifestRepository implementation."""

from __future__ import annotations

import json
from dataclasses import fields
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.infra.db.models.workspace_manifest import workspace_manifests


class WorkspaceManifestRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, manifest: WorkspaceManifest) -> WorkspaceManifest:
        stmt = workspace_manifests.insert().values(
            run_id=manifest.run_id,  # type: ignore[attr-defined]
            body=json.dumps(_manifest_to_dict(manifest)),
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return manifest

    async def get(self, run_id: str) -> WorkspaceManifest | None:
        stmt = workspace_manifests.select().where(
            workspace_manifests.c.run_id == run_id
        )
        result = await self._session.execute(stmt)
        row = result.fetchone()
        if row is None:
            return None
        return _dict_to_manifest(row.body)


def _dc_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a frozen dataclass to a dict without relying on dict()."""
    return {f.name: getattr(obj, f.name) for f in fields(obj)}


def _manifest_to_dict(m: WorkspaceManifest) -> dict[str, Any]:
    return {
        "inputs": [_dc_to_dict(i) for i in m.inputs],
        "writable_paths": [_dc_to_dict(p) for p in m.writable_paths],
        "outputs": [_dc_to_dict(o) for o in m.outputs],
        "network_policy": _dc_to_dict(m.network_policy),
        "tool_policy": _dc_to_dict(m.tool_policy),
        "secret_scope": _dc_to_dict(m.secret_scope),
        "snapshot_policy": _dc_to_dict(m.snapshot_policy),
    }


def _dict_to_manifest(body: str) -> WorkspaceManifest:
    data = json.loads(body)
    return WorkspaceManifest(  # type: ignore[arg-type]
        inputs=[type("IM", (), d) for d in data["inputs"]],  # type: ignore[list-item]
        writable_paths=[type("WP", (), d) for d in data["writable_paths"]],  # type: ignore[list-item]
        outputs=[type("OC", (), d) for d in data["outputs"]],  # type: ignore[list-item]
        network_policy=type("NP", (), data["network_policy"]),  # type: ignore[arg-type]
        tool_policy=type("TP", (), data["tool_policy"]),  # type: ignore[arg-type]
        secret_scope=type("SS", (), data["secret_scope"]),  # type: ignore[arg-type]
        snapshot_policy=type("SP", (), data["snapshot_policy"]),  # type: ignore[arg-type]
    )
