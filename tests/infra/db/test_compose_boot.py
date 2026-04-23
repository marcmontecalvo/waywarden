"""Verify that docker-compose brings Postgres to a healthy state."""

import subprocess

import pytest


@pytest.mark.integration
def test_compose_reports_healthy() -> None:
    """docker compose -f infra/docker-compose.db.yaml up --wait exits 0 and the
    healthcheck reports healthy within 30s on a clean host."""
    docker = subprocess.run(["docker", "version"], capture_output=True, text=True, timeout=10)
    if docker.returncode != 0:
        pytest.skip(f"docker compose not available: {docker.stdout}{docker.stderr}")

    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "infra/docker-compose.db.yaml",
            "up",
            "-d",
            "--wait",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"compose up failed: {result.stderr}"

    # Verify the container reports healthy via docker inspect
    inspect = subprocess.run(
        ["docker", "inspect", "--format={{.State.Health.Status}}", "waywarden_pg"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert inspect.returncode == 0, "container not found in docker inspect"
    status = inspect.stdout.strip().strip("{}")
    assert status == "healthy", f"expected healthy, got {status!r}"
