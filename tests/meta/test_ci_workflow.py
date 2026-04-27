"""Verify CI workflow keeps the coverage gate honest."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yaml"


def _load_ci_workflow() -> dict[str, object]:
    loaded = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return cast(dict[str, object], loaded)


def _step_run(job: dict[str, object], step_name: str) -> str:
    steps = job["steps"]
    assert isinstance(steps, list)
    for step in steps:
        assert isinstance(step, dict)
        if step.get("name") == step_name:
            run = step.get("run")
            assert isinstance(run, str)
            return run
    raise AssertionError(f"step {step_name!r} not found")


def test_non_integration_matrix_runs_without_coverage_gate() -> None:
    """Cross-platform non-integration tests should not enforce partial coverage."""
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    test_job = jobs["test"]
    assert isinstance(test_job, dict)
    run = _step_run(test_job, "Test")
    assert run == 'uv run pytest --no-cov -m "not integration"'


def test_linux_full_suite_job_carries_honest_coverage_gate() -> None:
    """The Linux Postgres-backed job must run the full suite with coverage."""
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    full_suite_job = jobs["integration-linux"]
    assert isinstance(full_suite_job, dict)
    run = _step_run(full_suite_job, "Run full test suite")
    assert run == "uv run pytest"
