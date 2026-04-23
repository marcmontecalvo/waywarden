import pytest

from waywarden.domain.profile import ProfileDescriptor, ProfileId, RequiredProviders


def test_profile_descriptor_construction_normalizes_values() -> None:
    descriptor = ProfileDescriptor(
        id=ProfileId(" ea "),
        display_name="  Executive Assistant  ",
        version="1.2.3",
        supported_extensions=(" skill ", "prompt", "team"),
        required_providers=RequiredProviders(
            model="fake-model",
            memory="fake-memory",
            knowledge="fake-knowledge",
        ),
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
        required_providers=RequiredProviders(
            model="fake-model",
            memory="fake-memory",
            knowledge="fake-knowledge",
        ),
    )
    right = ProfileDescriptor(
        id=ProfileId("coding"),
        display_name="Coding",
        version="1.0.0",
        supported_extensions=("command", "tool", "skill"),
        required_providers=RequiredProviders(
            model="fake-model",
            memory="fake-memory",
            knowledge="fake-knowledge",
        ),
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
                "required_providers": RequiredProviders(
                    model="fake-model",
                    memory="fake-memory",
                    knowledge="fake-knowledge",
                ),
            },
        ),
        (
            "display_name",
            {
                "id": "ea",
                "display_name": "   ",
                "version": "1.0.0",
                "supported_extensions": ("skill",),
                "required_providers": RequiredProviders(
                    model="fake-model",
                    memory="fake-memory",
                    knowledge="fake-knowledge",
                ),
            },
        ),
        (
            "version",
            {
                "id": "ea",
                "display_name": "Executive Assistant",
                "version": "1.0",
                "supported_extensions": ("skill",),
                "required_providers": RequiredProviders(
                    model="fake-model",
                    memory="fake-memory",
                    knowledge="fake-knowledge",
                ),
            },
        ),
    ],
)
def test_profile_descriptor_rejects_invalid_required_fields(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match=field_name):
        ProfileDescriptor(**kwargs)  # type: ignore[arg-type]


def test_profile_descriptor_rejects_empty_supported_extensions() -> None:
    with pytest.raises(ValueError, match="supported_extensions"):
        ProfileDescriptor(
            id=ProfileId("ea"),
            display_name="Executive Assistant",
            version="1.0.0",
            supported_extensions=(),
            required_providers=RequiredProviders(
                model="fake-model",
                memory="fake-memory",
                knowledge="fake-knowledge",
            ),
        )


def test_profile_descriptor_rejects_unknown_supported_extensions() -> None:
    with pytest.raises(ValueError, match="lowercase extension slug"):
        ProfileDescriptor(
            id=ProfileId("ea"),
            display_name="Executive Assistant",
            version="1.0.0",
            supported_extensions=("Memory Provider",),
            required_providers=RequiredProviders(
                model="fake-model",
                memory="fake-memory",
                knowledge="fake-knowledge",
            ),
        )


def test_profile_descriptor_rejects_duplicate_supported_extensions() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        ProfileDescriptor(
            id=ProfileId("ea"),
            display_name="Executive Assistant",
            version="1.0.0",
            supported_extensions=("skill", "prompt", "skill"),
            required_providers=RequiredProviders(
                model="fake-model",
                memory="fake-memory",
                knowledge="fake-knowledge",
            ),
        )


def test_profile_descriptor_rejects_untyped_required_providers() -> None:
    with pytest.raises(TypeError, match="RequiredProviders object"):
        ProfileDescriptor(
            id=ProfileId("ea"),
            display_name="Executive Assistant",
            version="1.0.0",
            supported_extensions=("skill",),
            required_providers={  # type: ignore[arg-type]
                "model": "fake-model",
                "memory": "fake-memory",
                "knowledge": "fake-knowledge",
            },
        )
