"""Static scan to ensure channel adapters never import repositories.

Channel adapters must stay transport-bound and never leak into domain
repositories or the DB layer.
"""

from __future__ import annotations

from pathlib import Path

_CHANNELS_ROOT = (
    Path(__file__).resolve().parent.parent.parent / "waywarden" / "adapters" / "channel"
)

_REPO_IMPORT_PATHS = (
    "waywarden.domain.repositories",
    "waywarden.infra.db",
)


def _scan_file_for_imports(filepath: Path) -> list[str]:
    """Return list of matched forbidden import prefixes found in *filepath*."""
    found: list[str] = []
    content = filepath.read_text(encoding="utf-8")
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for prefix in _REPO_IMPORT_PATHS:
            if prefix in stripped:
                found.append(f"{filepath.name}:{stripped}")
    return found


def test_channels_have_no_repo_imports() -> None:
    bad_lines: list[str] = []
    for source_file in sorted(_CHANNELS_ROOT.glob("*.py")):
        violations = _scan_file_for_imports(source_file)
        bad_lines.extend(violations)

    if bad_lines:
        header = "Channel adapters must not import repositories or DB modules."
        lines = [header]
        lines.extend(f"- {v}" for v in bad_lines)
        raise AssertionError("\n".join(lines))
