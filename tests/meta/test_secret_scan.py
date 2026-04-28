"""Verify secret-scan configuration stays auditable."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_gitleaks_ignore_has_no_unjustified_allowlist_entries() -> None:
    """Assert secret-scan allowlist entries are comments-only unless justified."""
    ignore_file = ROOT / ".gitleaksignore"
    entries = [
        line.strip()
        for line in ignore_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert entries == [], "non-comment .gitleaksignore entries require a documented justification"


def test_ci_runbook_documents_p7_fixture_secret_scan_status() -> None:
    """Assert the CI runbook documents the current P7 fixture allowlist posture."""
    ci_runbook = ROOT / "docs" / "setup" / "ci.md"
    text = ci_runbook.read_text(encoding="utf-8")

    assert "P7 adversarial fixtures currently require no `.gitleaksignore` entries." in text
    assert "Any future fixture allowlist entry must include an inline justification" in text
