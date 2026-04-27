"""PlanRevision — first-class plan revision artifact.

Each plan revision is a typed artifact with:
- A version-numbered body
- A diff-from-previous (semantic diff)
- A rationale explaining why the revision was needed
- An accumulation of prior revisions for audit trail

Opaque re-planning is disallowed: every revision must carry a rationale
and be surfaced as a ``run.artifact_created`` milestone (RT-002).

Canonical references:
    - Issue #98 (P6-7)
    - ADR 0007 (good patterns: boring persistence)
    - RT-002 §Artifact events
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class PlanRevision:
    """A single plan revision with diff-from-previous and rationale.

    Parameters
    ----------
    version:
        Sequential revision number (1-based).
    body:
        The plan body text for this revision.
    diff_from_previous:
        Human-readable diff describing what changed since version-1.
        Empty for the first revision.
    rationale:
        Why this revision was produced — must explain the reason
        for divergence from the prior plan.
    timestamp:
        When this revision was created.
    artifact_ref:
        Persistent reference to the plan artifact (e.g. ``artifact://plan-v2``).
    """

    version: int
    body: str
    diff_from_previous: str
    rationale: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    artifact_ref: str = ""

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("PlanRevision version must be >= 1")
        if not self.body:
            raise ValueError("PlanRevision body must not be empty")
        if not self.rationale:
            raise ValueError("PlanRevision rationale must not be empty")
        # First revision has no diff.
        if self.version == 1 and self.diff_from_previous:
            raise ValueError("First revision (version 1) must have an empty diff_from_previous")

    @property
    def is_first(self) -> bool:
        """True for the initial plan (version 1)."""
        return self.version == 1


@dataclass(frozen=True, slots=True)
class PlanRevisionCatalog:
    """Accumulator for plan revisions within a single coding run.

    Provides a clean API for producing the Nth revision and detecting
    redundant revisions (where the new plan is unchanged from the
    previous one).
    """

    revisions: tuple[PlanRevision, ...] = field(default_factory=tuple)

    @property
    def latest(self) -> PlanRevision | None:
        """Return the most recent revision, or None if empty."""
        return self.revisions[-1] if self.revisions else None

    @property
    def count(self) -> int:
        """Number of revisions in the catalog."""
        return len(self.revisions)

    def next_version(self) -> int:
        """Return the version number for the next revision."""
        return self.count + 1

    def add_revision(
        self,
        body: str,
        diff_from_previous: str,
        rationale: str,
    ) -> "PlanRevisionCatalog":
        """Append a new revision, detecting redundancy.

        Returns
        -------
        PlanRevisionCatalog
            A new catalog with the revision appended.

        Raises
        ------
        ValueError
            When the new body is identical to the latest revision
            (redundant revision rejection).
        """
        latest = self.latest
        if latest is not None and body == latest.body:
            raise ValueError(
                f"Redundant revision: plan body unchanged since version {latest.version}"
            )

        version = self.next_version()
        artifact_ref = f"artifact://plan-v{version}"
        revision = PlanRevision(
            version=version,
            body=body,
            diff_from_previous=diff_from_previous,
            rationale=rationale,
            timestamp=datetime.now(UTC),
            artifact_ref=artifact_ref,
        )
        return PlanRevisionCatalog(revisions=self.revisions + (revision,))
