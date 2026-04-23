from pathlib import Path

import pytest

from waywarden.config import InstanceLoadError, load_instances
from waywarden.domain.ids import InstanceId


def test_load_instances_loads_checked_in_fixture() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    registry = load_instances(
        config_dir=repo_root / "config",
        profiles_dir=repo_root / "profiles",
    )

    assert list(registry) == [InstanceId("marc-ea")]
    assert registry["marc-ea"].display_name == "Marc EA"
    assert registry["marc-ea"].profile_id == "ea"
    assert registry["marc-ea"].config_path == Path("instances/marc-ea.yaml")
    with pytest.raises(TypeError):
        registry[InstanceId("new")] = registry["marc-ea"]  # type: ignore[index]


def test_load_instances_aggregates_invalid_schema_and_profile_reference(
    tmp_path: Path,
) -> None:
    profiles_dir = tmp_path / "profiles"
    (profiles_dir / "ea").mkdir(parents=True)
    (profiles_dir / "ea" / "profile.yaml").write_text(
        "id: ea\n"
        "display_name: Executive Assistant\n"
        "version: 1.0.0\n"
        "required_providers:\n"
        "  model: fake-model\n"
        "  memory: fake-memory\n"
        "  knowledge: fake-knowledge\n"
        "supported_extensions:\n"
        "  - skill\n",
        encoding="utf-8",
    )

    config_dir = tmp_path / "config"
    (config_dir / "instances").mkdir(parents=True)
    (config_dir / "instances.yaml").write_text(
        "instances:\n"
        "  - id: broken\n"
        "    display_name: '   '\n"
        "    profile_id: ea\n"
        "    config_path: instances/broken.yaml\n"
        "  - id: lisa-ea\n"
        "    display_name: Lisa EA\n"
        "    profile_id: missing\n"
        "    config_path: instances/lisa-ea.yaml\n",
        encoding="utf-8",
    )
    (config_dir / "instances" / "broken.yaml").write_text(
        "env: {}\noverrides: {}\n",
        encoding="utf-8",
    )
    (config_dir / "instances" / "lisa-ea.yaml").write_text(
        "env: {}\noverrides: {}\n",
        encoding="utf-8",
    )

    with pytest.raises(InstanceLoadError) as exc_info:
        load_instances(config_dir=config_dir, profiles_dir=profiles_dir)

    message = str(exc_info.value)
    assert "Instance loading failed:" in message
    assert "instances[0]" in message
    assert "display_name must not be blank" in message
    assert "instances[1]" in message
    assert "profile_id 'missing' does not match any checked-in profile" in message


def test_load_instances_parses_multiple_instances_deterministically(tmp_path: Path) -> None:
    profiles_dir = tmp_path / "profiles"
    for profile_id, display_name in (("ea", "Executive Assistant"), ("coding", "Coding")):
        (profiles_dir / profile_id).mkdir(parents=True)
        (profiles_dir / profile_id / "profile.yaml").write_text(
            f"id: {profile_id}\n"
            f"display_name: {display_name}\n"
            "version: 1.0.0\n"
            "required_providers:\n"
            "  model: fake-model\n"
            "  memory: fake-memory\n"
            "  knowledge: fake-knowledge\n"
            "supported_extensions:\n"
            "  - skill\n",
            encoding="utf-8",
        )

    config_dir = tmp_path / "config"
    (config_dir / "instances").mkdir(parents=True)
    (config_dir / "instances.yaml").write_text(
        "instances:\n"
        "  - id: zeta\n"
        "    display_name: Zeta\n"
        "    profile_id: coding\n"
        "    config_path: instances/zeta.yaml\n"
        "  - id: alpha\n"
        "    display_name: Alpha\n"
        "    profile_id: ea\n"
        "    config_path: instances/alpha.yaml\n",
        encoding="utf-8",
    )
    (config_dir / "instances" / "zeta.yaml").write_text(
        "env: {}\noverrides: {}\n",
        encoding="utf-8",
    )
    (config_dir / "instances" / "alpha.yaml").write_text(
        "env:\n  WAYWARDEN_ENV: dev\noverrides: {}\n",
        encoding="utf-8",
    )

    registry = load_instances(config_dir=config_dir, profiles_dir=profiles_dir)

    assert list(registry) == [InstanceId("alpha"), InstanceId("zeta")]
    assert registry["alpha"].profile_id == "ea"
    assert registry["zeta"].profile_id == "coding"
