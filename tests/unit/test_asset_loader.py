"""Tests for the asset loader and profile-filtering engine (P5-2 #82)."""

from pathlib import Path

import pytest

from waywarden.assets.loader import (
    AssetLoadError,
    AssetNotFoundError,
    AssetRegistry,
    FilterError,
    FilterExpression,
)
from waywarden.assets.schema import (
    AssetKind,
    AssetMetadata,
    PipelineMetadata,
    WorkflowMetadata,
)

FIXTURES_DIR = Path("tests/fixtures/assets").resolve()


# -----------------------------------------------------------------------
# AssetRegistry — loading
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_from_dir_populates_registry() -> None:
    """Loading from the fixture dir should find all asset.yaml files."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    assert reg.is_valid
    all_assets = reg.all_assets()
    assert len(all_assets) == 3


@pytest.mark.asyncio
async def test_load_single_asset() -> None:
    """Load assets from a specific subdirectory."""
    asset_path = FIXTURES_DIR / "widgets" / "dashboard"
    reg = AssetRegistry()
    await reg.load_from_dir(asset_path)
    assert reg.is_valid
    assert len(reg.all_assets()) == 1


@pytest.mark.asyncio
async def test_load_nonexistent_dir_records_error() -> None:
    """Loading a non-existent directory records an error but doesn't crash."""
    reg = AssetRegistry()
    await reg.load_from_dir(Path("/no/such/dir"))
    assert not reg.is_valid
    assert len(reg.errors) >= 1


# -----------------------------------------------------------------------
# AssetRegistry — lookups
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_kind_returns_typed_assets() -> None:
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    return_value = reg.get_by_kind("widget")
    assert all(a.kind == "widget" for a in return_value)


@pytest.mark.asyncio
async def test_get_raises_when_missing() -> None:
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    with pytest.raises(AssetNotFoundError):
        reg.get("nonexistent", "widget")


@pytest.mark.asyncio
async def test_get_by_kind_filtering() -> None:
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    widgets = reg.get_by_kind("widget")
    policies = reg.get_by_kind("policy")
    assert len(widgets) == 2
    assert len(policies) == 1


# -----------------------------------------------------------------------
# FilterExpression — parsing
# -----------------------------------------------------------------------


def test_filter_from_dict_include() -> None:
    expr = FilterExpression.from_dict({"op": "include", "tags": ["ea"]})
    assert expr.op == "include"
    assert expr.select == {"tags": ["ea"]}


def test_filter_from_dict_exclude() -> None:
    expr = FilterExpression.from_dict({"op": "exclude", "tags": ["ui"]})
    assert expr.op == "exclude"


def test_filter_from_dict_by_tag() -> None:
    expr = FilterExpression.from_dict({"op": "by_tag", "tags": ["ea"]})
    assert expr.op == "by_tag"


def test_filter_from_dict_by_required_provider() -> None:
    expr = FilterExpression.from_dict({"op": "by_required_provider", "providers": ["model"]})
    assert expr.op == "by_required_provider"


def test_filter_missing_op_raises() -> None:
    with pytest.raises(FilterError):
        FilterExpression.from_dict({"tags": ["ea"]})


def test_filter_unknown_op_raises() -> None:
    with pytest.raises(FilterError):
        FilterExpression.from_dict({"op": "skip"})


# -----------------------------------------------------------------------
# FilterExpression — matching
# -----------------------------------------------------------------------


def _make_asset(
    *,
    id: str = "test",
    kind: AssetKind = "widget",
    tags: tuple[str, ...] = ("ea", "ui"),
    required_providers: tuple[str, ...] = ("model",),
) -> AssetMetadata:
    return AssetMetadata(
        id=id,
        kind=kind,
        version="1.0",
        description="d",
        tags=tags,
        required_providers=required_providers,
    )


def test_filter_include_matches_tags() -> None:
    asset = _make_asset()
    expr = FilterExpression.from_dict({"op": "include", "tags": ["ea"]})
    assert expr.matches(asset)


def test_filter_include_no_match() -> None:
    asset = _make_asset()
    expr = FilterExpression.from_dict({"op": "include", "tags": ["missing"]})
    assert not expr.matches(asset)


def test_filter_include_no_select_matches_all() -> None:
    asset = _make_asset()
    expr = FilterExpression.from_dict({"op": "include"})
    assert expr.matches(asset)


def test_filter_exclude_removes_matching() -> None:
    asset = _make_asset()
    expr = FilterExpression.from_dict({"op": "exclude", "tags": ["ea"]})
    # matches() returns True when the filter matches (i.e. should be excluded)
    assert expr.matches(asset)


def test_filter_by_tag_matches() -> None:
    asset = _make_asset()
    expr = FilterExpression.from_dict({"op": "by_tag", "tags": ["ea"]})
    assert expr.matches(asset)


def test_filter_by_required_provider_matches() -> None:
    asset = _make_asset()
    expr = FilterExpression.from_dict({"op": "by_required_provider", "providers": ["model"]})
    assert expr.matches(asset)


# -----------------------------------------------------------------------
# FilterExpression — evaluation
# -----------------------------------------------------------------------


def test_filter_evaluate_include() -> None:
    a1 = _make_asset(tags=("ea",))
    a2 = _make_asset(tags=("ua",))
    expr = FilterExpression.from_dict({"op": "include", "tags": ["ea"]})
    result = expr.evaluate([a1, a2])
    assert len(result) == 1
    assert result[0].id == "test"


def test_filter_evaluate_exclude() -> None:
    a1 = _make_asset(tags=("ea",))
    a2 = _make_asset(tags=("ua",))
    expr = FilterExpression.from_dict({"op": "exclude", "tags": ["ea"]})
    result = expr.evaluate([a1, a2])
    assert len(result) == 1
    assert result[0].tags == ("ua",)


# -----------------------------------------------------------------------
# AssetRegistry — filtering integration
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_filters_include() -> None:
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    filtered = reg.apply_filters([{"op": "include", "tags": ["ui"]}])
    assert all("ui" in a.tags for a in filtered)


def test_filter_expression_to_dict() -> None:
    expr = FilterExpression.from_dict({"op": "include", "tags": ["ea"]})
    data = expr.to_dict()
    assert data["op"] == "include"
    assert data["tags"] == ["ea"]


def test_pipeline_metadata_requires_typed_nodes_and_routes() -> None:
    asset = AssetMetadata.from_dict(
        {
            "id": "coding-review-pipeline",
            "kind": "pipeline",
            "version": "1.0.0",
            "description": "Pipeline with team execution and review checkpoint.",
            "nodes": [
                {
                    "id": "team-run",
                    "kind": "team",
                    "ref_id": "coding-dispatch-team",
                    "input_artifact_kind": "team-handoff",
                    "output_artifact_kind": "team-handoff",
                    "phase": "handoff",
                    "milestone": "team_started",
                },
                {
                    "id": "review-gate",
                    "kind": "review_checkpoint",
                    "ref_id": "adversarial-review",
                    "input_artifact_kind": "team-handoff",
                    "output_artifact_kind": "review-report",
                    "phase": "review",
                    "milestone": "findings_recorded",
                    "review_checkpoint": {
                        "input_artifact_kind": "team-handoff",
                        "passed_output_artifact_kind": "approved-handoff",
                        "failed_output_artifact_kind": "review-findings",
                    },
                },
            ],
            "routes": [
                {"from_node": "team-run", "outcome": "success", "to_node": "review-gate"},
                {"from_node": "review-gate", "outcome": "success", "to_node": None},
                {"from_node": "review-gate", "outcome": "failure", "to_node": "team-run"},
            ],
            "start_node": "team-run",
        }
    )

    assert isinstance(asset, PipelineMetadata)
    assert asset.start_node == "team-run"
    assert asset.nodes[1]["review_checkpoint"]["failed_output_artifact_kind"] == ("review-findings")


def test_workflow_metadata_requires_typed_handoff_contract() -> None:
    asset = AssetMetadata.from_dict(
        {
            "id": "coding-dispatcher-workflow",
            "kind": "workflow",
            "version": "1.0.0",
            "description": "Dispatcher workflow packaging.",
            "workflow_type": "dispatcher",
            "dispatcher": "agent-dispatcher",
            "team_ref": "coding-dispatch-team",
            "pipeline_ref": "coding-review-pipeline",
            "handoff_artifact": {
                "artifact_kind": "team-handoff",
                "label": "Coding team handoff",
                "output_name": "team-handoff",
            },
            "expected_outputs": ["plan", "patch", "review"],
        }
    )

    assert isinstance(asset, WorkflowMetadata)
    assert asset.handoff_artifact.artifact_kind == "team-handoff"
    assert asset.expected_outputs == ("plan", "patch", "review")


# -----------------------------------------------------------------------
# Chained filtering
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chained_filters() -> None:
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    result = reg.apply_filters(
        [
            {"op": "include", "tags": ["ui"]},
            {"op": "exclude", "tags": ["dashboard"]},
        ]
    )
    # After include by "ui" tag we get 2 widgets
    # After exclude we remove the dashboard widget
    assert len(result) >= 1
    for a in result:
        assert "ui" in a.tags


# -----------------------------------------------------------------------
# load_and_filter convenience
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_and_filter() -> None:
    reg = AssetRegistry()
    result = await reg.load_and_filter(
        FIXTURES_DIR,
        [{"op": "include", "tags": ["ea"]}],
    )
    assert len(result) >= 1
    assert all("ea" in a.tags for a in result)


@pytest.mark.asyncio
async def test_load_and_filter_exposes_load_errors() -> None:
    reg = AssetRegistry()
    with pytest.raises(AssetLoadError):
        await reg.load_and_filter(
            Path("/no/such/path"),
            [],
        )
