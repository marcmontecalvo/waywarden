import pytest

from waywarden.domain.profile import ProfileDescriptor, ProfileId


def test_profile_descriptor_construction_normalizes_values() -> None:
    descriptor = ProfileDescriptor(
        id=" ea ",
        display_name="  Executive Assistant  ",
        version="1.2.3",
        supported_extensions=(" skill ", "prompt", "team"),
    )

    assert descriptor.id == ProfileId("ea")
    assert descriptor.display_name == "Executive Assistant"
    assert descriptor.version == "1.2.3"
    assert descriptor.supported_extensions == ("skill", "prompt", "team")


def test_profile_descriptor_equality_is_value_based() -> None:
    left = ProfileDescriptor(
        id=ProfileId("coding"),
        display_name="Coding",
        version="1.0.0",
        supported_extensions=("command", "tool", "skill"),
    )
    right = ProfileDescriptor(
        id="coding",
        display_name="Coding",
        version="1.0.0",
        supported_extensions=("command", "tool", "skill"),
    )

    assert left == right


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        (
            "id",
            {
                "id": "   ",
                "display_name": "Executive Assistant",
                "version": "1.0.0",
                "supported_extensions": ("skill",),
            },
        ),
        (
            "display_name",
            {
                "id": "ea",
                "display_name": "   ",
                "version": "1.0.0",
                "supported_extensions": ("skill",),
            },
        ),
        (
            "version",
            {
                "id": "ea",
                "display_name": "Executive Assistant",
                "version": "1.0",
                "supported_extensions": ("skill",),
            },
        ),
    ],
)
def test_profile_descriptor_rejects_invalid_required_fields(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match=field_name):
        ProfileDescriptor(**kwargs)


def test_profile_descriptor_rejects_empty_supported_extensions() -> None:
    with pytest.raises(ValueError, match="supported_extensions"):
        ProfileDescriptor(
            id="ea",
            display_name="Executive Assistant",
            version="1.0.0",
            supported_extensions=(),
        )


def test_profile_descriptor_rejects_unknown_supported_extensions() -> None:
    with pytest.raises(ValueError, match="lowercase extension slug"):
        ProfileDescriptor(
            id="ea",
            display_name="Executive Assistant",
            version="1.0.0",
            supported_extensions=("Memory Provider",),
        )


def test_profile_descriptor_rejects_duplicate_supported_extensions() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        ProfileDescriptor(
            id="ea",
            display_name="Executive Assistant",
            version="1.0.0",
            supported_extensions=("skill", "prompt", "skill"),
        )
