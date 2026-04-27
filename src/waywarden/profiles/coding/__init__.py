"""Coding profile hydration (P6-1 #92).

Provides the ``CodingProfileView`` and hydration logic for the coding profile.
"""

from waywarden.profiles.coding.hydrate import (
    CodingProfileHydrationError,
    CodingProfileView,
    hydrate_coding_profile,
)

__all__ = [
    "CodingProfileHydrationError",
    "CodingProfileView",
    "hydrate_coding_profile",
]
