"""Verify that coverage configuration enforces the 80% gate."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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
