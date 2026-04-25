"""Shared-asset domain models and metadata schema.

Every asset under ``assets/<kind>/<id>/`` declares a typed metadata
record through the ``AssetMetadata`` model (and kind-specific
sub-classes).  This is the foundation for the asset loader and
profile-filtering engine (P5-2 #82).
"""

from waywarden.assets.loader import (
    AssetLoadError,
    AssetNotFoundError,
    AssetRegistry,
    FilterError,
    FilterExpression,
)
from waywarden.assets.schema import (
    KNOWN_ASSET_KINDS,
    AssetKind,
    AssetMetadata,
    AssetValidationError,
    validate_unique_ids,
)

__all__ = [
    "AssetKind",
    "AssetLoadError",
    "AssetMetadata",
    "AssetNotFoundError",
    "AssetRegistry",
    "AssetValidationError",
    "FilterError",
    "FilterExpression",
    "KNOWN_ASSET_KINDS",
    "validate_unique_ids",
]
