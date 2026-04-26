"""Coding profile overlay hydration (P6-1 #92).

Hydrates ``profiles/coding/profile.yaml`` into a typed coding profile that:
- declares its required providers via ``RequiredProviders``
- resolves asset-filter expansions through the AssetRegistry
- fails fast on startup when required providers or assets are missing

Canonical references:
    - ADR 0002 (core + profile packs)
    - ADR 0006 (V1 roadmap)
    - P3-2 #53 (profile.required_providers)
    - P5-2 #82 (AssetRegistry)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from waywarden.assets.loader import AssetRegistry
from waywarden.assets.schema import AssetMetadata
from waywarden.domain.profile import (
    ProfileDescriptor,
    ProfileId,
    ProfileRegistry,
    RequiredProviders,
)

# ---------------------------------------------------------------------------
# Domain error
# ---------------------------------------------------------------------------


class CodingProfileHydrationError(RuntimeError):
    """Raised when coding profile hydration fails."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(self.__str__())

    def __str__(self) -> str:
        lines = ["Coding profile hydration failed:"]
        lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Enriched profile descriptor
# ---------------------------------------------------------------------------


@dataclass
class CodingProfileView:
    """Enriched coding profile view with hydrated asset filters.

    This is the runtime-visible profile after hydration.
    """

    descriptor: ProfileDescriptor
    asset_filters: list[dict[str, Any]] = field(
        default_factory=list
    )
    resolved_assets: list[AssetMetadata] = field(
        default_factory=list
    )

    @property
    def id(self) -> ProfileId:
        return self.descriptor.id

    @property
    def display_name(self) -> str:
        return self.descriptor.display_name

    @property
    def required_providers(self) -> RequiredProviders:
        return self.descriptor.required_providers


# ---------------------------------------------------------------------------
# Hydration engine
# ---------------------------------------------------------------------------


def hydrate_coding_profile(
    profile_path: Path | None = None,
    *,
    profile_registry: ProfileRegistry | None = None,
    asset_registry: AssetRegistry | None = None,
    registry_assets_dir: str = "assets",
) -> CodingProfileView:
    """Hydrate the coding profile from its YAML manifest.

    Args:
        profile_path: Path to the coding profile YAML
            (``profiles/coding/profile.yaml``).
            If not supplied, looks up ``profiles/coding/profile.yaml``
            relative to cwd.
        profile_registry: Optional pre-built ProfileRegistry.
            If not supplied, the default coding profile is loaded.
        asset_registry: Optional pre-built AssetRegistry for filter expansion.
        registry_assets_dir: Directory to pass to ``AssetRegistry.load_from_dir``.

    Raises:
        CodingProfileHydrationError: When any validation or resolution fails.
    """
    errors: list[str] = []

    # 1. Load the raw profile descriptor from YAML.
    raw_profile = _load_raw_profile(profile_path, errors)
    if profile_registry is None:
        profile_registry = _build_profile_registry(raw_profile, errors)

    # 2. Get the coding profile descriptor.
    coding_descriptor = _get_coding_descriptor(
        profile_registry, errors
    )

    # 3. Extract ``asset_filters`` from the raw YAML.
    asset_filters = raw_profile.get("asset_filters", [])

    # 4. Expand filters through the asset registry.
    asset_reg = asset_registry
    if asset_reg is None:
        asset_reg = AssetRegistry()
        _sync_load_assets(asset_reg, registry_assets_dir)

    resolved_assets: list[AssetMetadata] = []
    if asset_filters and asset_reg.is_valid:
        resolved_assets = asset_reg.apply_filters(asset_filters)

    # 5. Collect all errors.
    errors.extend(asset_reg.errors)

    if errors:
        raise CodingProfileHydrationError(errors) from None

    return CodingProfileView(
        descriptor=coding_descriptor,
        asset_filters=asset_filters if asset_filters else [],
        resolved_assets=resolved_assets,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sync_load_assets(reg: AssetRegistry, assets_dir: str) -> None:
    """Run async asset loading synchronously (caching the result)."""
    import asyncio

    async def _do() -> None:
        await reg.load_from_dir(assets_dir)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        import threading

        result: list[BaseException | None] = [None]

        def _run() -> None:
            try:
                asyncio.get_event_loop().run_until_complete(_do())
            except BaseException as exc:  # noqa: BLE001
                result[0] = exc

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join()
        if result[0] is not None:
            raise result[0]
    else:
        loop.run_until_complete(_do())


def _load_raw_profile(
    profile_path: Path | None, errors: list[str]
) -> dict[str, Any]:
    if profile_path is None:
        profile_path = Path("profiles/coding/profile.yaml")
    try:
        content = yaml.safe_load(
            profile_path.read_text(encoding="utf-8")
        )
    except OSError as exc:
        errors.append(f"{profile_path}: read error: {exc}")
        return {}
    if content is None or not isinstance(content, dict):
        errors.append(
            f"{profile_path}: expected a mapping of profile settings"
        )
        return {}
    return content if isinstance(content, dict) else {}


def _build_profile_registry(
    raw: dict[str, Any], errors: list[str]
) -> ProfileRegistry:
    """Build a minimal ProfileRegistry from a raw YAML dict.

    If required_providers cannot be parsed, the descriptor is built with a
    stub value and the error is recorded so the caller flushes it.
    """
    try:
        raw_providers = raw.get("required_providers", {})
        required_providers = RequiredProviders(**raw_providers)
    except (TypeError, ValueError) as exc:
        # Build a stub descriptor so ProfileRegistry still has a key.
        # The caller will surface this error via the errors list.
        stub_providers = RequiredProviders(
            model="stub",
            memory="stub",
            knowledge="stub",
            tracer="noop",
        )
        stub_extensions = tuple(raw.get("supported_extensions") or ["noop"])
        descriptor = ProfileDescriptor(
            id=raw.get("id", "coding-noop"),
            display_name=raw.get("display_name", "Coding No-Op"),
            version=raw.get("version", "0.0.0"),
            supported_extensions=stub_extensions,
            required_providers=stub_providers,
        )
        errors.append(f"required_providers: {exc}")
        return ProfileRegistry({descriptor.id: descriptor})

    supported_extensions = tuple(
        raw.get("supported_extensions", [])
    )

    descriptor = ProfileDescriptor(
        id=raw.get("id", "coding-noop"),
        display_name=raw.get("display_name", "Coding No-Op"),
        version=raw.get("version", "0.0.0"),
        supported_extensions=supported_extensions,
        required_providers=required_providers,
    )
    return ProfileRegistry({descriptor.id: descriptor})


def _get_coding_descriptor(
    registry: ProfileRegistry, errors: list[str]
) -> ProfileDescriptor:
    """Return the coding profile descriptor or record an error."""
    try:
        return registry["coding"]
    except KeyError:
        errors.append(
            "Coding profile ('coding') not found in profile registry; "
            "checked-in profiles: "
            f"{[p.id for p in registry.list()]}"
        )
        raise CodingProfileHydrationError(errors) from None
