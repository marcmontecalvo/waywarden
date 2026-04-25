"""EA profile overlay hydration (P5-3 #83).

Provides the ``EAProfileView`` and hydration logic for the EA profile.
"""

from waywarden.profiles.ea.hydrate import (
    EAProfileView,
    ProfileHydrationError,
    hydrate_ea_profile,
)

__all__ = [
    "EAProfileView",
    "ProfileHydrationError",
    "hydrate_ea_profile",
]
