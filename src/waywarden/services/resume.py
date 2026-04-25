"""Resume service — crash-resume (worker recovery) from durable state.

Drives ``rehydrate_all()`` on server startup: for each non-terminal run,
rehydrate the Run record + latest RT-001 manifest version + RunEvent history,
verify the manifest hasn't drifted, and emit ``run.resumed(resume_kind="worker_recovery")``.

See Also
--------
- ``src/waywarden/services/resume_errors.py`` — typed exceptions
- ``src/waywarden/services/run_lifecycle.py`` — ``RunLifecycleService`` (resume verb)
- ``src/waywarden/services/orchestration/service.py`` — orchestration pipeline
"""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

import yaml

from waywarden.domain.manifest.content_hash import content_hash
from waywarden.domain.run import Run, RunState
from waywarden.services.resume_errors import (
    CrossRunCheckpointError,
    ManifestChangedWithoutRevisionError,
    ResumeServiceError,
)

logger = getLogger(__name__)

# Non-terminal states that are candidates for resume.
_RESUMABLE_STATES: frozenset[RunState] = frozenset(
    ["created", "planning", "executing", "waiting_approval"]
)

_TERMINAL_STATES: frozenset[RunState] = frozenset(
    ["completed", "failed", "cancelled"]
)

if TYPE_CHECKING:
    from waywarden.domain.manifest.manifest import WorkspaceManifest
    from waywarden.domain.repositories import (
        RunEventRepository,
        RunRepository,
        WorkspaceManifestRepository,
    )
    from waywarden.services.orchestration.service import (
        OrchestrationService,
    )


class ResumeService:
    """Rehydrates non-terminal runs on startup and emits resume events.

    Parameters
    ----------
    runs:
        RunRepository for queries.
    events:
        RunEventRepository for event history.
    manifests:
        WorkspaceManifestRepository for rehydrated manifests.
    lifecycle:
        RunLifecycleService for the underlying resume verb.
    orchestration:
        OrchestrationService for handing off resumed runs.
    """

    def __init__(
        self,
        runs: RunRepository,
        events: RunEventRepository,
        manifests: WorkspaceManifestRepository,
        lifecycle: object,
        orchestration: object,
        resume_on_startup: bool = False,
    ) -> None:
        self._runs = runs
        self._events = events
        self._manifests = manifests
        self._lifecycle = lifecycle
        self._orchestration = orchestration
        self.resume_on_startup = resume_on_startup

    async def rehydrate_all(self) -> list[Run]:
        """Rehydrate all non-terminal runs.

        Returns
        -------
        List of rehydrated ``Run`` objects that were successfully resumed.

        Raises
        ------
        ManifestChangedWithoutRevisionError:
            If a run's manifest drifted since last attachment.
        """
        resumed: list[Run] = []

        # Load all pending run configurations from the instances config.
        pending = await self._load_pending_runs_yaml()

        for pending_run in pending:
            run_id = pending_run.run_id
            expected_hash = pending_run.manifest_hash
            checkpoint_run_id = pending_run.checkpoint_run_id

            # Fetch the latest persisted run state.
            existing = await self._runs.get(str(run_id))
            if existing is None:
                logger.debug("rehydrate: run %s not found in DB, skipping", run_id)
                continue

            if existing.state in _TERMINAL_STATES:
                logger.debug("rehydrate: run %s is terminal (%s), skipping", run_id, existing.state)
                continue

            # 1. Verify checkpoint ownership if present.
            if checkpoint_run_id is not None and checkpoint_run_id != str(run_id):
                raise CrossRunCheckpointError(checkpoint_run_id, str(run_id))

            # 2. Verify manifest has not drifted.
            if expected_hash is not None:
                actual_hash = await self._compute_actual_manifest_hash(run_id)
                if actual_hash != expected_hash:
                    raise ManifestChangedWithoutRevisionError(str(run_id))

            # 3. Emit run.resumed (worker_recovery).
            try:
                await self._lifecycle.resume(  # type: ignore[attr-defined]
                    run_id,
                    resume_kind="worker_recovery",
                )
            except Exception as exc:
                # Lifecycle-level failure — mark as resume_blocked via progress.
                logger.warning("rehydrate: resume failed for run %s: %s", run_id, exc)
                await self._emit_resume_blocked(run_id, str(exc))
                continue

            resumed.append(existing)

        return resumed

    # -- private helpers ----------------------------------------------------

    async def _load_pending_runs_yaml(self) -> list[_PendingRunConfig]:
        """Load pending runs from ``data/partner-auxiliary/pending-runs.yaml``.

        File structure (minimal variant):
        ```yaml
        pending_runs:
          - run_id: run-uuid-1
            manifest_hash: abc123...
            checkpoint_run_id: null
        ```
        """
        from pathlib import Path

        pending_path = Path("data/partner-auxiliary/pending-runs.yaml")
        if not pending_path.exists():
            return []

        with open(pending_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        results: list[_PendingRunConfig] = []
        for item in data.get("pending_runs", []):
            results.append(
                _PendingRunConfig(
                    run_id=item["run_id"],
                    manifest_hash=item.get("manifest_hash"),
                    checkpoint_run_id=item.get("checkpoint_run_id"),
                )
            )
        return results

    async def _compute_actual_manifest_hash(self, run_id: str) -> str:
        """Compute SHA-256 of the persisted manifest body for *run_id*.

        Returns the hex digest of the manifest body stored in the database.
        """
        manifest = await self._manifests.get(run_id)
        if manifest is not None:
            body = await self._serialize_manifest_body(manifest)
            return content_hash(body)
        # No manifest found — compute hash from empty string so it
        # will never match. This effectively blocks resume when
        # no manifest exists.
        return content_hash("")

    async def _serialize_manifest_body(self, manifest: object) -> str:
        """Serialize a ``WorkspaceManifest`` to its canonical JSON body."""
        import json

        from dataclasses import asdict

        if hasattr(manifest, "__dataclass_fields__"):
            body_dict = asdict(manifest)  # type: ignore[call-overload]
            # Sort keys for deterministic hashing
            return json.dumps(body_dict, sort_keys=True, separators=(",", ":"))
        return json.dumps(manifest, sort_keys=True, separators=(",", ":"))

    async def _emit_resume_blocked(self, run_id: str, reason: str) -> None:
        """Emit a ``run.progress(phase="execute", milestone="resume_blocked")`` event."""
        from datetime import UTC, datetime

        from waywarden.domain.ids import RunEventId, RunId
        from waywarden.domain.run_event import Actor, Causation, RunEvent

        latest = await self._events.latest_seq(run_id)
        event = RunEvent(
            id=RunEventId(f"evt-{run_id}-resume-blocked"),
            run_id=RunId(run_id),
            seq=latest + 1,
            type="run.progress",
            payload={"phase": "execute", "milestone": "resume_blocked"},
            timestamp=datetime.now(UTC),
            causation=Causation(
                event_id=None,
                action="resume_blocked",
                request_id=None,
            ),
            actor=Actor(kind="system", id=None, display=None),
        )
        await self._events.append(event)


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------


class _PendingRunConfig:
    """Lightweight struct for a single pending-run entry from the YAML config."""

    __slots__ = ("run_id", "manifest_hash", "checkpoint_run_id")

    def __init__(
        self,
        run_id: str,
        manifest_hash: str | None,
        checkpoint_run_id: str | None,
    ) -> None:
        self.run_id = run_id
        self.manifest_hash = manifest_hash
        self.checkpoint_run_id = checkpoint_run_id
