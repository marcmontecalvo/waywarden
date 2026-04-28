"""Tests for the till-done loop routine (P6-4 #95)."""

from __future__ import annotations

from typing import cast

import pytest

from waywarden.domain.durability import TokenBudgetTelemetry
from waywarden.services.orchestration.milestones import MILESTONE_CATALOG
from waywarden.services.orchestration.tilldone import (
    IterationResult,
    LoopConfig,
    LoopOutcome,
    _EventStream,
    run_till_done,
)

# ---------------------------------------------------------------------------
# Milestone catalog validation
# ---------------------------------------------------------------------------


def test_code_phase_exists_in_milestones() -> None:
    """The code phase is declared with required till-done milestones."""
    code_milestones = [m for m in MILESTONE_CATALOG if m.phase == "code"]
    expected = {
        "iteration_started",
        "changes_applied",
        "check_passed",
        "check_failed",
        "plan_revised",
        "iteration_complete",
        "loop_escalated",
        "terminal",
    }
    actual = {m.milestone for m in code_milestones}
    assert expected.issubset(actual)


# ---------------------------------------------------------------------------
# Single-pass completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_pass_success() -> None:
    """First iteration succeeds -> COMPLETED."""
    result = await run_till_done(
        "run-1",
        iteration_result_fn=lambda i: IterationResult(
            plan_artifact_id="plan-v1",
            check_passed=True,
            changes_applied=True,
            plan_revised=False,
        ),
    )
    assert result == LoopOutcome.COMPLETED


@pytest.mark.asyncio
async def test_till_done_progress_includes_token_budget_metadata_when_supplied() -> None:
    """Token telemetry is surfaced as metadata only, without changing loop control."""
    stream = _EventStream()

    result = await run_till_done(
        "run-budget",
        iteration_result_fn=lambda i: IterationResult(
            plan_artifact_id="plan-v1",
            check_passed=True,
            changes_applied=True,
            plan_revised=False,
        ),
        token_budget=TokenBudgetTelemetry(
            budget_id="budget-loop-1",
            source="instance",
            observed_total_tokens=300,
            remaining_tokens=700,
            warning="within-budget",
        ),
        events=stream,
    )

    assert result == LoopOutcome.COMPLETED
    assert stream.progress_events
    assert all(
        cast(dict[str, object], event.payload["token_budget"])["budget_id"] == "budget-loop-1"
        for event in stream.progress_events
    )


# ---------------------------------------------------------------------------
# Multi-iteration completion with first check failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_iteration_completes_after_retry() -> None:
    """Check failure -> plan revision -> second iteration succeeds."""
    results = [
        IterationResult(
            plan_artifact_id="plan-v1",
            check_passed=False,
            plan_revised=True,
            iteration_count=1,
        ),
        IterationResult(
            plan_artifact_id="plan-v2",
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

    result = await run_till_done("run-1", iteration_result_fn=fn)
    assert result == LoopOutcome.COMPLETED


# ---------------------------------------------------------------------------
# Escalation from consecutive check failures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escalation_after_check_failures() -> None:
    """Consecutive failures hit check_failure_max -> ESCALATED."""
    results = [
        IterationResult(
            plan_artifact_id="plan-v1",
            check_passed=False,
            changes_applied=False,
            plan_revised=False,
        ),
        IterationResult(
            plan_artifact_id="plan-v2",
            check_passed=False,
            changes_applied=False,
            plan_revised=False,
        ),
        IterationResult(
            plan_artifact_id="plan-v3",
            check_passed=False,
            changes_applied=False,
            plan_revised=False,
        ),
    ]
    idx = [0]

    def fn(iter_no: int) -> IterationResult:
        r = results[idx[0]]
        idx[0] += 1
        return r

    result = await run_till_done(
        "run-1",
        iteration_result_fn=fn,
        config=LoopConfig(
            max_iterations=3,
            check_failure_max=2,
            esc_check_if_revised=False,
        ),
    )
    assert result == LoopOutcome.ESCALATED


# ---------------------------------------------------------------------------
# Escalation from exceeding max iterations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escalation_on_max_iterations() -> None:
    """Max iterations reached -> ESCALATED."""
    results = [
        IterationResult(
            plan_artifact_id=f"plan-v{i}",
            check_passed=False,
            changes_applied=False,
            plan_revised=False,
        )
        for i in range(3)
    ]
    idx = [0]

    def fn(iter_no: int) -> IterationResult:
        r = results[idx[0]]
        idx[0] += 1
        return r

    result = await run_till_done(
        "run-1",
        iteration_result_fn=fn,
        config=LoopConfig(
            max_iterations=3,
            check_failure_max=5,
            esc_check_if_revised=False,
        ),
    )
    assert result == LoopOutcome.ESCALATED


# ---------------------------------------------------------------------------
# Escalation from plan revision with esc_check_if_revised=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escalation_on_plan_revision_revised() -> None:
    """Plan revision with esc_check_if_revised increments failure counter."""
    results = [
        IterationResult(
            plan_artifact_id="plan-v1",
            check_passed=False,
            plan_revised=True,
        ),
        IterationResult(
            plan_artifact_id="plan-v2",
            check_passed=False,
            plan_revised=True,
        ),
        IterationResult(
            plan_artifact_id="plan-v3",
            check_passed=False,
            plan_revised=True,
        ),
    ]
    idx = [0]

    def fn(iter_no: int) -> IterationResult:
        r = results[idx[0]]
        idx[0] += 1
        return r

    result = await run_till_done(
        "run-1",
        iteration_result_fn=fn,
        config=LoopConfig(
            max_iterations=3,
            check_failure_max=2,
            esc_check_if_revised=True,
        ),
    )
    assert result == LoopOutcome.ESCALATED
