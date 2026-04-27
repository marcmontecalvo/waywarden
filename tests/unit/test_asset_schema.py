"""Tests for the shared-asset metadata schema (P5-1 #81)."""

import pytest

from waywarden.assets.schema import (
    KNOWN_ASSET_KINDS,
    AgentMetadata,
    AssetMetadata,
    AssetValidationError,
    CommandMetadata,
    ContextProviderMetadata,
    PipelineMetadata,
    PolicyMetadata,
    ProfileOverlayMetadata,
    PromptMetadata,
    RoutineMetadata,
    SkillMetadata,
    TeamMetadata,
    ThemeMetadata,
    ToolMetadata,
    WidgetMetadata,
    validate_unique_ids,
)

# -----------------------------------------------------------------------
# AssetMetadata — required fields
# -----------------------------------------------------------------------


def test_required_fields_are_set() -> None:
    """AssetMetadata can be constructed with only required fields."""
    meta = AssetMetadata(
        id="test-asset",
        kind="prompt",
        version="1.0.0",
        description="A test asset",
    )
    assert meta.id == "test-asset"
    assert meta.kind == "prompt"
    assert meta.version == "1.0.0"
    assert meta.description == "A test asset"
    assert meta.tags == ()
    assert meta.required_providers == ()
    assert meta.profile_filter == ()


def test_description_must_not_be_blank() -> None:
    with pytest.raises(AssetValidationError):
        AssetMetadata.from_dict(
            {
                "id": "x",
                "kind": "prompt",
                "version": "1.0.0",
                "description": "",
            }
        )


# -----------------------------------------------------------------------
# Version coercion
# -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_ver", "expected"),
    [
        ("1", "1.0.0"),
        ("1.2", "1.2.0"),
        ("1.2.3", "1.2.3"),
        ("1.2.3-beta.1", "1.2.3-beta.1"),
        ("1.2.3+meta", "1.2.3+meta"),
        (" 1.2.3 ", "1.2.3"),
    ],
)
def test_version_coercion(input_ver: str, expected: str) -> None:
    meta = AssetMetadata(id="v", kind="prompt", version=input_ver, description="d")
    assert meta.version == expected


def test_version_coerces_via_from_dict() -> None:
    meta = AssetMetadata.from_dict(
        {"id": "v", "kind": "prompt", "version": "0", "description": "d"}
    )
    assert meta.version == "0.0.0"


# -----------------------------------------------------------------------
# ID normalisation
# -----------------------------------------------------------------------


def test_id_is_lowercased_and_stripped() -> None:
    meta = AssetMetadata(
        id="  My-Asset_ID ",
        kind="prompt",
        version="1.0.0",
        description="d",
    )
    assert meta.id == "my-asset_id"


def test_id_rejects_blank() -> None:
    with pytest.raises(AssetValidationError):
        AssetMetadata.from_dict(
            {
                "id": "  ",
                "kind": "prompt",
                "version": "1.0.0",
                "description": "d",
            }
        )


# -----------------------------------------------------------------------
# Invalid kinds are rejected
# -----------------------------------------------------------------------


def test_invalid_kind_rejected() -> None:
    with pytest.raises(AssetValidationError):
        AssetMetadata.from_dict(
            {
                "id": "x",
                "kind": "flashlight",
                "version": "1.0.0",
                "description": "d",
            }
        )


# -----------------------------------------------------------------------
# Tags normalisation and dedup
# -----------------------------------------------------------------------


def test_tags_coerce_single_string_to_tuple() -> None:
    meta = AssetMetadata(
        id="t",
        kind="prompt",
        version="1.0.0",
        description="d",
        tags=("alpha", "beta"),
    )
    assert meta.tags == ("alpha", "beta")


def test_tags_deduplicate() -> None:
    meta = AssetMetadata(
        id="td",
        kind="prompt",
        version="1.0.0",
        description="d",
        tags=("a", "a", "b"),
    )
    assert meta.tags == ("a", "b")


def test_tags_empty_strings_filtered() -> None:
    meta = AssetMetadata(
        id="te",
        kind="prompt",
        version="1.0.0",
        description="d",
        tags=("a", "  ", "b"),
    )
    assert meta.tags == ("a", "b")


# -----------------------------------------------------------------------
# Required providers normalisation
# -----------------------------------------------------------------------


def test_required_providers_normalized_and_deduped() -> None:
    meta = AssetMetadata(
        id="rp",
        kind="prompt",
        version="1.0.0",
        description="d",
        required_providers=("Fake-Model", "fake-model", "honcho"),
    )
    assert meta.required_providers == ("fake-model", "honcho")


# -----------------------------------------------------------------------
# Profile filter validation
# -----------------------------------------------------------------------


def test_profile_filter_requires_op() -> None:
    with pytest.raises(AssetValidationError):
        AssetMetadata.from_dict(
            {
                "id": "pf",
                "kind": "prompt",
                "version": "1.0.0",
                "description": "d",
                "profile_filter": [{"tag": "ea"}],
            }
        )


def test_profile_filter_valid_include() -> None:
    meta = AssetMetadata.from_dict(
        {
            "id": "pf",
            "kind": "prompt",
            "version": "1.0.0",
            "description": "d",
            "profile_filter": [{"op": "include", "tag": "ea"}],
        }
    )
    assert meta.profile_filter == ({"op": "include", "tag": "ea"},)


def test_profile_filter_invalid_op_rejected() -> None:
    with pytest.raises(AssetValidationError):
        AssetMetadata.from_dict(
            {
                "id": "pf",
                "kind": "prompt",
                "version": "1.0.0",
                "description": "d",
                "profile_filter": [{"op": "skip", "tag": "ea"}],
            }
        )


def test_profile_filter_empty_list_allowed() -> None:
    meta = AssetMetadata.from_dict(
        {
            "id": "pf",
            "kind": "prompt",
            "version": "1.0.0",
            "description": "d",
            "profile_filter": [],
        }
    )
    assert meta.profile_filter == ()


def test_profile_filter_none_allowed() -> None:
    meta = AssetMetadata.from_dict(
        {
            "id": "pf",
            "kind": "prompt",
            "version": "1.0.0",
            "description": "d",
            "profile_filter": None,
        }
    )
    assert meta.profile_filter == ()


# -----------------------------------------------------------------------
# Kind-specific metadata models
# -----------------------------------------------------------------------


def test_routine_metadata_has_extra_fields() -> None:
    meta = RoutineMetadata(
        id="briefing",
        kind="routine",
        version="1.0.0",
        description="a briefing",
        milestones=(
            {"phase": "intake", "names": ["received", "accepted"]},
            {"phase": "plan", "names": ["drafted", "ready"]},
        ),
        emits_events=("run.progress",),
    )
    assert meta.milestones[0]["phase"] == "intake"
    assert meta.emits_events == ("run.progress",)


def test_from_dict_dispatches_to_routine_metadata() -> None:
    meta = AssetMetadata.from_dict(
        {
            "id": "briefing",
            "kind": "routine",
            "version": "1.0.0",
            "description": "a briefing",
            "milestones": [{"phase": "intake", "names": ["received"]}],
            "emits_events": ["run.progress"],
        }
    )

    assert isinstance(meta, RoutineMetadata)
    assert meta.milestones[0]["phase"] == "intake"


def test_agent_metadata_enforces_max_tools_per_step_minimum() -> None:
    with pytest.raises(Exception):  # noqa PT011
        AgentMetadata(
            id="bad-agent",
            kind="agent",
            version="1.0.0",
            description="d",
            max_tools_per_step=0,
        )


def test_policy_metadata_enforce_mode() -> None:
    meta = PolicyMetadata(
        id="strict",
        kind="policy",
        version="1.0.0",
        description="strict policy",
        enforce_mode="block",
    )
    assert meta.enforce_mode == "block"


def test_kind_literal_stick() -> None:
    """Each kind-specific model locks its ``kind`` literal."""
    assert RoutineMetadata(kind="routine", id="r", version="1.0", description="d").kind == "routine"
    assert WidgetMetadata(kind="widget", id="w", version="1.0", description="d").kind == "widget"
    assert CommandMetadata(kind="command", id="c", version="1.0", description="d").kind == "command"
    assert PromptMetadata(kind="prompt", id="p", version="1.0", description="d").kind == "prompt"
    assert ToolMetadata(kind="tool", id="t", version="1.0", description="d").kind == "tool"
    assert SkillMetadata(kind="skill", id="s", version="1.0", description="d").kind == "skill"
    assert (
        AgentMetadata(
            kind="agent",
            id="a",
            version="1.0",
            description="d",
            max_tools_per_step=1,
        ).kind
        == "agent"
    )
    assert TeamMetadata(kind="team", id="tm", version="1.0", description="d").kind == "team"
    assert (
        PipelineMetadata(kind="pipeline", id="pl", version="1.0", description="d").kind
        == "pipeline"
    )
    assert PolicyMetadata(kind="policy", id="po", version="1.0", description="d").kind == "policy"
    assert ThemeMetadata(kind="theme", id="th", version="1.0", description="d").kind == "theme"
    assert (
        ContextProviderMetadata(
            kind="context_provider",
            id="cp",
            version="1.0",
            description="d",
        ).kind
        == "context_provider"
    )
    assert (
        ProfileOverlayMetadata(
            kind="profile_overlay",
            id="po2",
            version="1.0",
            description="d",
        ).kind
        == "profile_overlay"
    )


# -----------------------------------------------------------------------
# JSON schema export
# -----------------------------------------------------------------------


def test_to_json_schema_returns_dict() -> None:
    meta = AssetMetadata(
        id="base",
        kind="prompt",
        version="1.0.0",
        description="d",
    )
    schema = meta.to_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema


# -----------------------------------------------------------------------
# Cross-asset duplicate-id validation
# -----------------------------------------------------------------------


def test_validate_unique_ids_passes() -> None:
    assets = [
        AssetMetadata(id="alpha", kind="prompt", version="1.0", description="d"),
        AssetMetadata(id="beta", kind="widget", version="1.0", description="d"),
    ]
    assert validate_unique_ids(assets) == []


def test_validate_unique_ids_catches_duplicates_across_kinds() -> None:
    assets = [
        AssetMetadata(id="dup", kind="prompt", version="1.0", description="d"),
        AssetMetadata(id="dup", kind="widget", version="1.0", description="d"),
    ]
    errors = validate_unique_ids(assets)
    assert len(errors) == 1
    assert "dup" in errors[0]


def test_validate_unique_ids_no_duplicates_same_kind() -> None:
    assets = [
        AssetMetadata(id="x", kind="prompt", version="1.0", description="d"),
        AssetMetadata(id="x", kind="prompt", version="1.0", description="d"),
    ]
    errors = validate_unique_ids(assets)
    assert len(errors) == 1


# -----------------------------------------------------------------------
# All known asset kinds are valid
# -----------------------------------------------------------------------


def test_all_known_kinds_accepted() -> None:
    for kind in KNOWN_ASSET_KINDS:
        AssetMetadata(
            id=f"asset-for-{kind}",
            kind=kind,
            version="1.0.0",
            description="test",
        )


def test_current_profile_extension_examples_are_known_kinds() -> None:
    from waywarden.domain.profile import (
        CURRENT_PROFILE_EXTENSION_EXAMPLES,
    )

    assert KNOWN_ASSET_KINDS == CURRENT_PROFILE_EXTENSION_EXAMPLES
