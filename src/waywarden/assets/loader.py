"""Asset registry and profile-filtering engine.

Loads the ``assets/`` tree, validates every ``asset.yaml`` against the
P5-1 metadata schema (``AssetMetadata``), and exposes a typed registry
with profile-filter expressions (``include`` / ``exclude`` / by-tag /
by-required-provider).

Canonical references:
    - ADR 0002 (core + profile packs)
    - ADR 0011 (harness boundaries)
    - P5-1 #81 (metadata schema)
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from waywarden.assets.schema import (
    AssetKind,
    AssetMetadata,
    AssetValidationError,
    validate_unique_ids,
)

# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class AssetLoadError(ValueError):
    """Aggregated failure when loading assets."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(self.__str__())

    def __str__(self) -> str:
        lines = ["Asset loading failed:"]
        lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


class AssetNotFoundError(ValueError):
    """Raised when a registry lookup finds no asset."""

    def __init__(self, asset_id: str, kind: AssetKind | None = None) -> None:
        self.asset_id = asset_id
        self.kind = kind
        msg = f"asset {asset_id!r}"
        if kind is not None:
            msg += f" of kind {kind!r}"
        super().__init__(msg)


class FilterError(ValueError):
    """Raised when a profile filter expression is malformed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# Filter expressions
# ---------------------------------------------------------------------------


class FilterExpression:
    """A single typed filter expression.

    Supported operators:
        - ``include`` — select matching assets
        - ``exclude`` — remove matching assets
        - ``by_tag`` — select assets whose tags contain the given set
        - ``by_required_provider`` — select assets requiring the provider

    When multiple expressions exist they are applied in order
    (include → exclude → …).
    """

    __slots__ = ("op", "select")

    def __init__(
        self,
        op: str,
        select: dict[str, Any] | None = None,
    ) -> None:
        self.op = op.strip().lower()
        self.select: dict[str, Any] = select or {}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilterExpression:
        """Parse a filter expression from a dict (loaded from YAML)."""
        if "op" not in data:
            raise FilterError("filter expression missing 'op' field")
        op = data["op"].strip().lower()
        valid_ops = {"include", "exclude", "by_tag", "by_required_provider"}
        if op not in valid_ops:
            raise FilterError(
                f"unknown filter operation {data['op']!r}; expected one of {sorted(valid_ops)}"
            )
        select = {k: v for k, v in data.items() if k != "op" and v is not None}
        return cls(op=op, select=select)

    def matches(self, asset: AssetMetadata) -> bool:
        """Check whether a single asset satisfies this filter expression."""
        if self.op == "include":
            # An include with no select conditions matches everything.
            if not self.select:
                return True
            return self._match_include(asset)
        if self.op == "exclude":
            if not self.select:
                return True
            return self._match_exclude(asset)
        if self.op == "by_tag":
            return self._match_by_tag(asset)
        if self.op == "by_required_provider":
            return self._match_by_required_provider(asset)
        return False

    def _match_include(self, asset: AssetMetadata) -> bool:
        """Match by specific metadata fields."""
        if "tags" in self.select:
            include_tags = (
                self.select["tags"]
                if isinstance(self.select["tags"], (list, tuple))
                else [self.select["tags"]]
            )
            asset_set = set(asset.tags)
            for tag in include_tags:
                if tag not in asset_set:
                    return False
        if "required_providers" in self.select:
            include_providers = self.select["required_providers"]
            if not isinstance(include_providers, (list, tuple)):
                include_providers = [include_providers]
            asset_providers = set(asset.required_providers)
            for provider in include_providers:
                if provider not in asset_providers:
                    return False
        return True

    def _match_exclude(self, asset: AssetMetadata) -> bool:
        """Exclude assets matching the set."""
        return self._match_include(asset)

    def _match_by_tag(self, asset: AssetMetadata) -> bool:
        """Match assets that contain all given tags."""
        required_tags = self.select.get("tags") or self.select.get("tag")
        if required_tags is None:
            return False
        if isinstance(required_tags, str):
            required_tags = [required_tags]
        asset_set = set(asset.tags)
        return all(tag in asset_set for tag in required_tags)

    def _match_by_required_provider(self, asset: AssetMetadata) -> bool:
        """Match assets that require the given provider(s)."""
        providers = self.select.get("providers") or self.select.get("provider")
        if providers is None:
            return False
        if isinstance(providers, str):
            providers = [providers]
        asset_set = set(asset.required_providers)
        return any(p in asset_set for p in providers)

    def evaluate(
        self,
        assets: list[AssetMetadata],
    ) -> list[AssetMetadata]:
        """Evaluate this filter against a list of assets."""
        if self.op in {"include", "by_tag", "by_required_provider"}:
            return [a for a in assets if self.matches(a)]
        if self.op == "exclude":
            return [a for a in assets if not self.matches(a)]
        return assets

    def to_dict(self) -> dict[str, Any]:
        """Serialise back to a dict."""
        data: dict[str, Any] = {"op": self.op}
        data.update(self.select)
        return data


# ---------------------------------------------------------------------------
# AssetRegistry
# ---------------------------------------------------------------------------


class AssetRegistry:
    """In-memory registry of validated asset metadata.

    Provides:
        - Typed lookup by ``id`` + ``kind``.
        - Profile filter evaluation.
        - Fail-fast on missing or malformed files.
    """

    def __init__(self) -> None:
        # (id, kind) -> AssetMetadata
        self._assets_by_key: dict[tuple[str, AssetKind], AssetMetadata] = {}
        # id -> set of kinds it was seen with
        self._seen_ids: dict[str, list[AssetMetadata]] = defaultdict(list)
        self._errors: list[str] = []

    # ---- loading ----------------------------------------------------------

    async def load_from_dir(
        self,
        assets_dir: Path | str,
        *,
        recursive: bool = True,
    ) -> None:
        """Load all ``asset.yaml`` files under ``assets_dir``.

        Args:
            assets_dir: Root directory tree.
            recursive: Whether to recurse into subdirectories.
        """
        root = Path(assets_dir).resolve()
        if not root.is_dir():
            self._errors.append(f"{root.as_posix()}: not a directory")
            return

        pattern = "**/asset.yaml" if recursive else "asset.yaml"
        yaml_files = sorted(root.glob(pattern))

        if not yaml_files:
            self._errors.append(f"{root.as_posix()}: no asset.yaml files found")
            return

        for yaml_path in yaml_files:
            await self._load_single(yaml_path)

    async def _load_single(self, yaml_path: Path) -> None:
        """Load and validate a single asset.yaml."""
        try:
            content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except OSError as exc:
            self._errors.append(f"{yaml_path!r}: unable to read: {exc.strerror or exc}")
            return
        except yaml.YAMLError as exc:
            reason = getattr(exc, "problem", None) or str(exc)
            self._errors.append(f"{yaml_path!r}: YAML parse error: {reason}")
            return

        if content is None or not isinstance(content, dict):
            self._errors.append(f"{yaml_path!r}: expected a mapping of asset settings")
            return

        try:
            asset = AssetMetadata.from_dict(content)
        except AssetValidationError as exc:
            self._errors.extend(exc.errors)
            return

        key = (asset.id, asset.kind)
        if key in self._assets_by_key:
            self._errors.append(
                f"Duplicate asset key ({asset.id!r}, {asset.kind!r}) in {yaml_path!r}"
            )
            return

        self._assets_by_key[key] = asset
        self._seen_ids[asset.id].append(asset)

    @staticmethod
    def validate_cross_asset(
        assets: list[AssetMetadata],
    ) -> list[str]:
        """Run cross-asset validations (e.g. duplicate IDs)."""
        return validate_unique_ids(assets)

    @property
    def errors(self) -> list[str]:
        """All load/validation errors accumulated so far."""
        return list(self._errors)

    @property
    def is_valid(self) -> bool:
        """True when no load or validation errors occurred."""
        return len(self._errors) == 0

    # ---- lookups ----------------------------------------------------------

    def get(self, asset_id: str, kind: AssetKind) -> AssetMetadata:
        """Return an asset by id and kind.

        Raises ``AssetNotFoundError`` when not found.
        """
        key = (asset_id, kind)
        asset = self._assets_by_key.get(key)
        if asset is None:
            raise AssetNotFoundError(asset_id, kind)
        return asset

    def get_by_kind(self, kind: AssetKind) -> tuple[AssetMetadata, ...]:
        """Return all assets of a given kind."""
        return tuple(asset for (aid, ak), asset in self._assets_by_key.items() if ak == kind)

    def get_by_id(self, asset_id: str) -> tuple[AssetMetadata, ...]:
        """Return all assets matching an id (could span kinds)."""
        seen = self._seen_ids.get(asset_id, [])
        return tuple(seen)

    def all_assets(self) -> tuple[AssetMetadata, ...]:
        """Return all registered assets."""
        return tuple(self._assets_by_key.values())

    # ---- filtering --------------------------------------------------------

    def apply_filters(
        self,
        filters: list[dict[str, Any]],
    ) -> list[AssetMetadata]:
        """Apply a sequence of filter expressions against all assets.

        Filters are evaluated in order.  The output of each filter
        feeds into the next.
        """
        assets = list(self.all_assets())
        for filter_dict in filters:
            expr = FilterExpression.from_dict(filter_dict)
            assets = expr.evaluate(assets)
        return assets

    async def load_and_filter(
        self,
        assets_dir: Path | str,
        filters: list[dict[str, Any]],
        *,
        recursive: bool = True,
    ) -> list[AssetMetadata]:
        """Load all assets then apply filters.

        Convenience method that loads then filters in one call.
        """
        await self.load_from_dir(assets_dir, recursive=recursive)
        if not self.is_valid:
            raise AssetLoadError(self.errors)
        return self.apply_filters(filters)
