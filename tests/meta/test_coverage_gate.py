"""Verify that coverage configuration enforces the 80% gate."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P7_MODULES = {
    "src/waywarden/domain/subagent.py",
    "src/waywarden/domain/team.py",
    "src/waywarden/domain/pipeline.py",
    "src/waywarden/services/orchestration/adversarial_review.py",
    "src/waywarden/services/orchestration/dispatcher_workflow.py",
    "src/waywarden/services/orchestration/pipeline.py",
    "src/waywarden/services/orchestration/subagent_progress.py",
    "src/waywarden/services/orchestration/team_progress.py",
}


def test_fail_under_eighty() -> None:
    """Assert that pyproject.toml sets ``cov-fail-under=80``."""
    pyproject = ROOT / "pyproject.toml"
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    addopts = config["tool"]["pytest"]["ini_options"]["addopts"]
    assert "--cov-fail-under=80" in addopts, "coverage gate must be >= 80"


def test_coverage_source_includes_alembic() -> None:
    """Assert that alembic is included in coverage source."""
    pyproject = ROOT / "pyproject.toml"
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    source = config["tool"]["coverage"]["run"]["source"]
    assert "alembic" in source, "alembic must be in coverage source"


def test_coverage_source_includes_waywarden_source_only() -> None:
    """Assert that coverage measures app code, not test directories."""
    pyproject = ROOT / "pyproject.toml"
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    source = config["tool"]["coverage"]["run"]["source"]
    assert "src/waywarden" in source, "coverage must include the Waywarden source tree"
    assert not any(entry.startswith("tests/") for entry in source), (
        "coverage source must not include test directories in the denominator"
    )


def test_coverage_excludes_generated_migrations() -> None:
    """Assert that alembic version files are excluded from coverage."""
    pyproject = ROOT / "pyproject.toml"
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    omit = config["tool"]["coverage"]["run"]["omit"]
    assert any("alembic/versions" in o for o in omit), (
        "alembic/versions/*.py must be excluded from coverage"
    )


def test_p7_modules_are_in_coverage_denominator() -> None:
    """Assert P7 teams, pipelines, sub-agents, and adversarial modules are covered."""
    pyproject = ROOT / "pyproject.toml"
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    addopts = config["tool"]["pytest"]["ini_options"]["addopts"]
    source = set(config["tool"]["coverage"]["run"]["source"])
    omit = set(config["tool"]["coverage"]["run"]["omit"])

    assert "--cov=src/waywarden" in addopts
    assert "src/waywarden" in source
    for module in P7_MODULES:
        assert (ROOT / module).is_file(), f"{module} must exist before coverage can count it"
        assert module not in omit, f"{module} must not be omitted from coverage"


def test_coverage_omit_list_stays_narrow_and_explicit() -> None:
    """Assert coverage exclusions do not silently remove product modules."""
    pyproject = ROOT / "pyproject.toml"
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    omit = set(config["tool"]["coverage"]["run"]["omit"])

    assert omit == {
        "src/waywarden/__init__.py",
        "src/waywarden/infra/tracing/otel.py",
        "alembic/versions/*.py",
    }
