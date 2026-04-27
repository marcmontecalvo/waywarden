"""Tests for PlanRevision — first-class loop output (P6-7 #98).

Covers:
- Typed `PlanRevision` artifact construction
- Diff computation against prior plan
- Catalog milestone + artifact event on every revision
- Tests covering first plan, revision, redundant revision rejection
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from waywarden.services.orchestration.milestones import (
    MILESTONE_CATALOG,
    get_milestones,
)
from waywarden.services.orchestration.plan_revision import (
    PlanRevision,
    PlanRevisionCatalog,
)
from waywarden.services.orchestration.tilldone import (
    IterationResult,
    LoopConfig,
    LoopOutcome,
    _EventStream,
    run_till_done,
)

# ---------------------------------------------------------------------------
# PlanRevision data model tests
# ---------------------------------------------------------------------------


class TestPlanRevisionModel:
    """Tests for the typed PlanRevision artifact."""

    def test_plan_revision_first_version_required(self) -> None:
        """Version 1 is required for the first revision."""
        rev = PlanRevision(
            version=1,
            body="Initial plan to fix the login bug",
            diff_from_previous="",
            rationale="First draft based on intake analysis",
        )
        assert rev.version == 1
        assert rev.is_first
        assert rev.diff_from_previous == ""

    def test_plan_revision_version_increments(self) -> None:
        """Subsequent revisions have incrementing version numbers."""
        rev = PlanRevision(
            version=2,
            body="Revised plan: also fix the session timeout",
            diff_from_previous="- Fix login only\n+ Fix login and session timeout",
            rationale="Check failed: session timeout also causes login failures",
        )
        assert rev.version == 2
        assert not rev.is_first
        assert rev.diff_from_previous == "- Fix login only\n+ Fix login and session timeout"

    def test_plan_revision_requires_body(self) -> None:
        """Empty body is rejected."""
        with pytest.raises(ValueError, match="body must not be empty"):
            PlanRevision(
                version=2,
                body="",
                diff_from_previous="change",
                rationale="rationale",
            )

    def test_plan_revision_requires_rationale(self) -> None:
        """Empty rationale is rejected."""
        with pytest.raises(ValueError, match="rationale must not be empty"):
            PlanRevision(
                version=2,
                body="Some plan",
                diff_from_previous="",
                rationale="",
            )

    def test_plan_revision_rejects_version_zero(self) -> None:
        """Version numbers below 1 are rejected."""
        with pytest.raises(ValueError, match="must be >= 1"):
            PlanRevision(
                version=0,
                body="plan",
                diff_from_previous="",
                rationale="rationale",
            )

    def test_plan_revision_first_revision_has_no_diff(self) -> None:
        """First revision must have an empty diff_from_previous."""
        with pytest.raises(ValueError, match="must have an empty diff"):
            PlanRevision(
                version=1,
                body="Initial plan",
                diff_from_previous="unexpected diff",
                rationale="First",
            )


class TestPlanRevisionCatalog:
    """Tests for the PlanRevisionCatalog accumulator."""

    def test_empty_catalog_returns_none_latest(self) -> None:
        """An empty catalog has no latest revision."""
        catalog = PlanRevisionCatalog()
        assert catalog.latest is None
        assert catalog.count == 0

    def test_add_first_revision(self) -> None:
        """Adding the first revision creates version 1."""
        catalog = PlanRevisionCatalog()
        catalog = catalog.add_revision(
            body="Initial plan to refactor login",
            diff_from_previous="",
            rationale="First draft from code scanning",
        )
        assert catalog.count == 1
        rev = catalog.latest
        assert rev is not None
        assert rev.version == 1
        assert rev.is_first

    def test_add_revision_with_diff_and_rationale(self) -> None:
        """Second revision carries diff and rationale."""
        catalog = PlanRevisionCatalog()
        catalog = catalog.add_revision(
            body="Initial plan",
            diff_from_previous="",
            rationale="First draft",
        )
        catalog = catalog.add_revision(
            body="Revised plan: also handle edge cases",
            diff_from_previous="- Only main path\n+ Handle main path and edge cases",
            rationale="Check revealed unhandled edge cases",
        )
        assert catalog.count == 2
        assert catalog.latest is not None
        assert catalog.latest.version == 2
        assert catalog.latest.diff_from_previous == (
            "- Only main path\n+ Handle main path and edge cases"
        )
        assert catalog.latest.rationale == "Check revealed unhandled edge cases"

    def test_redundant_revision_rejected(self) -> None:
        """A plan body that matches the latest is rejected as redundant."""
        catalog = PlanRevisionCatalog()
        catalog = catalog.add_revision(
            body="Initial plan",
            diff_from_previous="",
            rationale="First",
        )
        with pytest.raises(ValueError, match="Redundant revision"):
            catalog.add_revision(
                body="Initial plan",
                diff_from_previous="",
                rationale="Same plan re-submitted",
            )

    def test_next_version_is_incremental(self) -> None:
        """next_version returns count + 1."""
        catalog = PlanRevisionCatalog()
        assert catalog.next_version() == 1
        catalog = catalog.add_revision("v1", "", "r1")
        assert catalog.next_version() == 2
        catalog = catalog.add_revision("v2", "d2", "r2")
        assert catalog.next_version() == 3


# ---------------------------------------------------------------------------
# Milestone catalog validation
# ---------------------------------------------------------------------------


def test_plan_revision_cataloged_milestone_exists() -> None:
    """The plan_revision_cataloged milestone is declared in the catalog."""
    catalog_entries = [m for m in MILESTONE_CATALOG if m.phase == "plan"]
    milestone_names = {m.milestone for m in catalog_entries}
    assert "revision_cataloged" in milestone_names


def test_plan_revised_milestone_exists() -> None:
    """The plan_revised milestone is declared in the code phase."""
    code_milestones = get_milestones("code")
    assert "plan_revised" in code_milestones


# ---------------------------------------------------------------------------
# Till-done loop — plan revision artifact emission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_till_done_with_plan_revision_emits_artifact() -> None:
    """When plan is revised, a plan-revision artifact is emitted."""
    stream = _EventStream()
    results = [
        IterationResult(
            plan_artifact_id="artifact://plan-v1",
            check_passed=False,
            plan_revised=True,
            iteration_count=1,
            plan_body="Plan v1: refactor login",
            plan_diff_from_previous="",
            plan_rationale="First plan drafted",
        ),
        IterationResult(
            plan_artifact_id="artifact://plan-v2",
            check_passed=True,
            plan_revised=False,
            changes_applied=True,
            iteration_count=2,
            plan_body="Plan v2: also handle edge cases",
            plan_diff_from_previous="- Only main path\n+ Handle edge cases",
            plan_rationale="Check revealed unhandled edge cases",
        ),
    ]
    idx = [0]

    def fn(iter_no: int) -> IterationResult:
        r = results[idx[0]]
        idx[0] += 1
        return r

    result = await run_till_done("run-rev-1", iteration_result_fn=fn, events=stream)

    assert result == LoopOutcome.COMPLETED

    # Check that plan revision artifact was emitted
    artifact_events = stream.artifact_events
    assert len(artifact_events) >= 1

    revision_artifacts = [
        e
        for e in artifact_events
        if isinstance(e.payload, Mapping) and e.payload.get("artifact_kind") == "plan-revision"
    ]
    assert len(revision_artifacts) == 1

    ar = revision_artifacts[0]
    payload = ar.payload
    assert isinstance(payload, Mapping)
    assert payload["artifact_kind"] == "plan-revision"
    assert payload["version"] == 1
    assert payload["rationale"] == "First plan drafted"
    assert payload["diff_from_previous"] == ""
    assert payload["body"] == "Plan v1: refactor login"


@pytest.mark.asyncio
async def test_till_done_multiple_revisions() -> None:
    """Multiple plan revisions each get their own artifact."""
    stream = _EventStream()
    results = [
        IterationResult(
            plan_artifact_id="artifact://plan-v1",
            check_passed=False,
            plan_revised=True,
            iteration_count=1,
            plan_body="Plan v1",
            plan_diff_from_previous="",
            plan_rationale="Initial",
        ),
        IterationResult(
            plan_artifact_id="artifact://plan-v2",
            check_passed=False,
            plan_revised=True,
            iteration_count=2,
            plan_body="Plan v2",
            plan_diff_from_previous="- v1\n+ v2",
            plan_rationale="More issues found",
        ),
        IterationResult(
            plan_artifact_id="artifact://plan-v3",
            check_passed=True,
            plan_revised=False,
            changes_applied=True,
            iteration_count=3,
            plan_body="Plan v3",
            plan_diff_from_previous="- v2\n+ v3",
            plan_rationale="Final fixes",
        ),
    ]
    idx = [0]

    def fn(iter_no: int) -> IterationResult:
        r = results[idx[0]]
        idx[0] += 1
        return r

    result = await run_till_done(
        "run-multi-rev",
        iteration_result_fn=fn,
        events=stream,
        config=LoopConfig(max_iterations=5, esc_check_if_revised=False),
    )

    assert result == LoopOutcome.COMPLETED

    revision_artifacts = [
        e
        for e in stream.artifact_events
        if isinstance(e.payload, Mapping) and e.payload.get("artifact_kind") == "plan-revision"
    ]
    assert len(revision_artifacts) == 2  # iterations 1 and 2 had plan_revised=True


@pytest.mark.asyncio
async def test_till_done_no_revision_no_artifact() -> None:
    """When plan is never revised, no plan-revision artifacts are emitted."""
    stream = _EventStream()
    results = [
        IterationResult(
            plan_artifact_id="artifact://plan-v1",
            check_passed=True,
            changes_applied=True,
            plan_revised=False,
            iteration_count=1,
        ),
    ]
    idx = [0]

    def fn(iter_no: int) -> IterationResult:
        r = results[idx[0]]
        idx[0] += 1
        return r

    result = await run_till_done("run-no-rev", iteration_result_fn=fn, events=stream)

    assert result == LoopOutcome.COMPLETED

    revision_artifacts = [
        e
        for e in stream.artifact_events
        if isinstance(e.payload, Mapping) and e.payload.get("artifact_kind") == "plan-revision"
    ]
    assert len(revision_artifacts) == 0


# ---------------------------------------------------------------------------
# Catalog milestone on revision
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revision_emits_plan_revision_cataloged_milestone() -> None:
    """When a plan is revised, the plan/revision_cataloged milestone fires."""
    stream = _EventStream()
    results = [
        IterationResult(
            plan_artifact_id="artifact://plan-v1",
            check_passed=False,
            plan_revised=True,
            iteration_count=1,
            plan_body="Plan v1",
            plan_diff_from_previous="",
            plan_rationale="Initial",
        ),
        IterationResult(
            plan_artifact_id="artifact://plan-v2",
            check_passed=True,
            changes_applied=True,
            plan_revised=False,
            iteration_count=2,
        ),
    ]
    idx = [0]

    def fn(iter_no: int) -> IterationResult:
        r = results[idx[0]]
        idx[0] += 1
        return r

    await run_till_done("run-milestone", iteration_result_fn=fn, events=stream)

    # Find the plan/revision_cataloged milestone events
    revision_cataloged = [
        e
        for e in stream.progress_events
        if isinstance(e.payload, Mapping)
        and e.payload.get("phase") == "plan"
        and e.payload.get("milestone") == "revision_cataloged"
    ]
    assert len(revision_cataloged) == 1


# ---------------------------------------------------------------------------
# Redundant revision rejection in API surface
# ---------------------------------------------------------------------------


def test_plan_revision_catalog_enforces_redo_propagation() -> None:
    """Non-redundant revisions are accepted sequentially."""
    catalog = PlanRevisionCatalog()

    catalog = catalog.add_revision(
        body="Step 1: read files",
        diff_from_previous="",
        rationale="Initial plan from code scan",
    )
    assert catalog.latest is not None
    assert catalog.latest.version == 1

    catalog = catalog.add_revision(
        body="Step 1: read files, then write patches",
        diff_from_previous="- Just read\n+ Read and write",
        rationale="Check failed: no write step in plan",
    )
    assert catalog.latest is not None
    assert catalog.latest.version == 2
    assert catalog.latest.diff_from_previous == "- Just read\n+ Read and write"
