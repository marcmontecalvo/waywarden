from pathlib import Path

import pytest

from waywarden.domain.instance import InstanceConfig, InstanceDescriptor, InstanceId


def test_instance_descriptor_construction_normalizes_values() -> None:
    descriptor = InstanceDescriptor(
        id="marc-ea",
        display_name="  Marc EA  ",
        profile_id=" ea ",
        config_path="config/instances/marc-ea.yaml",
    )

    assert descriptor.id == InstanceId("marc-ea")
    assert descriptor.display_name == "Marc EA"
    assert descriptor.profile_id == "ea"
    assert descriptor.config_path == Path("config/instances/marc-ea.yaml")


def test_instance_descriptor_equality_is_value_based() -> None:
    left = InstanceDescriptor(
        id=InstanceId("coding-main"),
        display_name="Coding Main",
        profile_id="coding",
        config_path=Path("config/instances/coding-main.yaml"),
    )
    right = InstanceDescriptor(
        id="coding-main",
        display_name="Coding Main",
        profile_id="coding",
        config_path="config/instances/coding-main.yaml",
    )

    assert left == right


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        (
            "id",
            {
                "id": "   ",
                "display_name": "Marc EA",
                "profile_id": "ea",
                "config_path": "config/instances/marc-ea.yaml",
            },
        ),
        (
            "display_name",
            {
                "id": "marc-ea",
                "display_name": "   ",
                "profile_id": "ea",
                "config_path": "config/instances/marc-ea.yaml",
            },
        ),
        (
            "profile_id",
            {
                "id": "marc-ea",
                "display_name": "Marc EA",
                "profile_id": "   ",
                "config_path": "config/instances/marc-ea.yaml",
            },
        ),
        (
            "config_path",
            {
                "id": "marc-ea",
                "display_name": "Marc EA",
                "profile_id": "ea",
                "config_path": "   ",
            },
        ),
    ],
)
def test_instance_descriptor_rejects_blank_required_fields(
    field_name: str,
    kwargs: dict[str, str],
) -> None:
    with pytest.raises(ValueError, match=field_name):
        InstanceDescriptor(**kwargs)


def test_instance_config_copies_mappings_and_supports_equality() -> None:
    source_env = {"WAYWARDEN_ENV": "dev"}
    source_overrides = {"token_budget": 2048}

    left = InstanceConfig(env=source_env, overrides=source_overrides)
    right = InstanceConfig(
        env={"WAYWARDEN_ENV": "dev"},
        overrides={"token_budget": 2048},
    )

    source_env["WAYWARDEN_ENV"] = "prod"
    source_overrides["token_budget"] = 999

    assert left == right
    assert left.env["WAYWARDEN_ENV"] == "dev"
    assert left.overrides["token_budget"] == 2048


def test_instance_config_rejects_blank_env_keys() -> None:
    with pytest.raises(ValueError, match="env key"):
        InstanceConfig(env={"   ": "value"})


def test_instance_config_rejects_non_string_env_values() -> None:
    with pytest.raises(TypeError, match="WAYWARDEN_ENV"):
        InstanceConfig(env={"WAYWARDEN_ENV": 1})  # type: ignore[arg-type]
