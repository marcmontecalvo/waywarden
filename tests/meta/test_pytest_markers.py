"""Verify that pytest markers are registered in pyproject.toml."""

import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_integration_marker_registered() -> None:
    """Assert that the ``integration`` marker is declared in pyproject.toml."""
    pyproject = ROOT / "pyproject.toml"
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    markers = config["tool"]["pytest"]["ini_options"]["markers"]
    marker_names = [m.split(":")[0].strip('"').strip("'") for m in markers]
    assert "integration" in marker_names, "pytest markers must declare 'integration'"


def test_no_strict_mode_violation() -> None:
    """Assert that running pytest with --strict-markers passes (no unknown markers)."""
    result = subprocess.run(
        ["uv", "run", "pytest", "--strict-markers", "--collect-only", "-q"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"--strict-markers failed: {result.stderr}"
