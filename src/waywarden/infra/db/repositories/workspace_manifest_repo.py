"""WorkspaceManifestRepository implementation."""

from __future__ import annotations

import json
from dataclasses import fields
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.ids import RunId
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.infra.db.models.workspace_manifest import workspace_manifests


class WorkspaceManifestRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, manifest: WorkspaceManifest) -> WorkspaceManifest:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        body_dict = _manifest_to_dict(manifest)
        body_json = json.dumps(body_dict)
        run_id_val = str(manifest.run_id)
        manifest_id = str(uuid4())

        # Use Postgres upsert when running on Postgres; plain insert for SQLite.
        if self._session.bind.dialect.name == "postgresql":
            stmt = (
                pg_insert(workspace_manifests)
                .values(  # type: ignore[arg-type]
                    id=manifest_id,
                    run_id=run_id_val,
                    body=body_json,
                )
                .on_conflict_do_update(
                    constraint="uq_workspace_manifests_run_id",
                    set_=dict(
                        body=workspace_manifests.c.body,  # type: ignore[union-attr]
                    ),
                )
            )
        else:
            stmt = workspace_manifests.insert().values(
                id=manifest_id,
                run_id=run_id_val,
                body=body_json,
            )
        await self._session.execute(stmt)
        await self._session.flush()
        return manifest

    async def get(self, run_id: str) -> WorkspaceManifest | None:
        stmt = workspace_manifests.select().where(workspace_manifests.c.run_id == run_id)
        result = await self._session.execute(stmt)
        row = result.fetchone()
        if row is None:
            return None
        return _dict_to_manifest(row.run_id, row.body)


def _dc_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a frozen dataclass to a dict, recursively handling nested dataclasses."""
    from dataclasses import is_dataclass

    if not is_dataclass(obj):
        return obj  # type: ignore[return-value]
    result: dict[str, Any] = {}
    for f in fields(obj):
        val = getattr(obj, f.name)
        if is_dataclass(val):
            result[f.name] = _dc_to_dict(val)
        elif isinstance(val, list):
            result[f.name] = [_dc_to_dict(item) if is_dataclass(item) else item for item in val]
        else:
            result[f.name] = val
    return result


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


def _dict_to_manifest(run_id: str, body: str) -> WorkspaceManifest:
    data = json.loads(body)
    return WorkspaceManifest(  # type: ignore[arg-type]
        run_id=RunId(run_id),
        inputs=[type("IM", (), d) for d in data["inputs"]],  # type: ignore[list-item]
        writable_paths=[type("WP", (), d) for d in data["writable_paths"]],  # type: ignore[list-item]
        outputs=[type("OC", (), d) for d in data["outputs"]],  # type: ignore[list-item]
        network_policy=type("NP", (), data["network_policy"]),  # type: ignore[arg-type]
        tool_policy=type("TP", (), data["tool_policy"]),  # type: ignore[arg-type]
        secret_scope=type("SS", (), data["secret_scope"]),  # type: ignore[arg-type]
        snapshot_policy=type("SP", (), data["snapshot_policy"]),  # type: ignore[arg-type]
    )
