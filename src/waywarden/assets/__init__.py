"""Shared-asset domain models and metadata schema.

Every asset under ``assets/<kind>/<id>/`` declares a typed metadata
record through the ``AssetMetadata`` model (and kind-specific
sub-classes).  This is the foundation for the asset loader and
profile-filtering engine (P5-2 #82).
"""

from waywarden.assets.schema import (
    KNOWN_ASSET_KINDS,
    AssetKind,
    AssetMetadata,
    AssetValidationError,
)

__all__ = [
    "AssetKind",
    "AssetMetadata",
    "AssetValidationError",
    "KNOWN_ASSET_KINDS",
]
