"""Resume service error types.

Typed exceptions used by ``ResumeService`` to distinguish manifest drift,
cross-run checkpoint violations, and other resume-path failures.
"""

from __future__ import annotations


class ResumeServiceError(RuntimeError):
    """Base error for resume service failures."""


class ManifestChangedWithoutRevisionError(ResumeServiceError):
    """Raised when the persisted manifest body changed without a new run revision.

    Attributes
    ----------
    run_id:
        The run whose manifest drifted.
    """

    def __init__(self, run_id: str) -> None:
        super().__init__(
            f"resume blocked: manifest for run {run_id!r} changed "
            "without a new run revision"
        )
        self.run_id = run_id


class CrossRunCheckpointError(ResumeServiceError):
    """Raised when a checkpoint resume references a different run.

    Attributes
    ----------
    checkpoint_run_id:
        The run that owns the checkpoint.
    target_run_id:
        The run the caller tried to resume against.
    """

    def __init__(
        self,
        checkpoint_run_id: str,
        target_run_id: str,
    ) -> None:
        super().__init__(
            f"cross-run checkpoint: checkpoint {checkpoint_run_id!r} "
            f"does not match target run {target_run_id!r}"
        )
        self.checkpoint_run_id = checkpoint_run_id
        self.target_run_id = target_run_id
