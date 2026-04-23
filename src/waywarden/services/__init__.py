"""Domain services for Waywarden.

Services sit between the provider protocol layer and concrete adapters,
assembling provider data into domain-level constructs (prompt scaffolding,
etc.) without leaking provider SDK types into the domain.
"""

from __future__ import annotations

from waywarden.services.context_builder import ContextBuilder

__all__ = ["ContextBuilder"]
