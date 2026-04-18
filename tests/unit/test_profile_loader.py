from pathlib import Path

import pytest

from waywarden.domain.profile import ProfileId
from waywarden.profiles import ProfileLoadError, load_profiles


def test_load_profiles_returns_empty_registry_for_empty_directory(tmp_path: Path) -> None:
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    registry = load_profiles(profiles_dir)

    assert len(registry) == 0
    assert list(registry.items()) == []


def test_load_profiles_loads_checked_in_profile_fixtures() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    registry = load_profiles(repo_root / "profiles")

    assert list(registry) == [
        ProfileId("coding"),
        ProfileId("ea"),
        ProfileId("home"),
    ]
    assert registry[ProfileId("ea")].display_name == "Executive Assistant"
    assert registry["coding"].supported_extensions == (
        "command",
        "prompt",
        "tool",
        "skill",
        "agent",
        "team",
        "pipeline",
        "policy",
        "theme",
        "context_provider",
        "profile_overlay",
    )
    with pytest.raises(TypeError):
        registry[ProfileId("new")] = registry["ea"]  # type: ignore[index]


def test_load_profiles_aggregates_invalid_profile_errors(tmp_path: Path) -> None:
    profiles_dir = tmp_path / "profiles"
    (profiles_dir / "valid").mkdir(parents=True)
    (profiles_dir / "valid" / "profile.yaml").write_text(
        "id: valid\ndisplay_name: Valid\nversion: 1.0.0\nsupported_extensions:\n  - skill\n",
        encoding="utf-8",
    )
    (profiles_dir / "broken-yaml").mkdir()
    (profiles_dir / "broken-yaml" / "profile.yaml").write_text(
        "id: broken\ndisplay_name: [broken\n",
        encoding="utf-8",
    )
    (profiles_dir / "broken-data").mkdir()
    (profiles_dir / "broken-data" / "profile.yaml").write_text(
        'id: broken-data\ndisplay_name: Broken\nversion: "1.0"\nsupported_extensions: []\n',
        encoding="utf-8",
    )

    with pytest.raises(ProfileLoadError) as exc_info:
        load_profiles(profiles_dir)

    message = str(exc_info.value)
    assert "Profile loading failed:" in message
    assert "broken-yaml/profile.yaml" in message
    assert "YAML parse error" in message
    assert "broken-data/profile.yaml" in message
    assert "semantic version like 1.0.0" in message


def test_load_profiles_rejects_duplicate_profile_ids_deterministically(
    tmp_path: Path,
) -> None:
    profiles_dir = tmp_path / "profiles"
    (profiles_dir / "alpha").mkdir(parents=True)
    (profiles_dir / "alpha" / "profile.yaml").write_text(
        "id: shared\ndisplay_name: Alpha\nversion: 1.0.0\nsupported_extensions:\n  - skill\n",
        encoding="utf-8",
    )
    (profiles_dir / "beta").mkdir()
    (profiles_dir / "beta" / "profile.yaml").write_text(
        "id: shared\ndisplay_name: Beta\nversion: 1.0.0\nsupported_extensions:\n  - prompt\n",
        encoding="utf-8",
    )

    with pytest.raises(ProfileLoadError) as exc_info:
        load_profiles(profiles_dir)

    message = str(exc_info.value)
    assert "profile id 'shared' is declared by multiple files" in message
    assert "alpha/profile.yaml" in message
    assert "beta/profile.yaml" in message
