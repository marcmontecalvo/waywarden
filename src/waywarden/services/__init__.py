"""Domain services for Waywarden.

Services sit between the provider protocol layer and concrete adapters,
assembling provider data into domain-level constructs (prompt scaffolding,
etc.) without leaking provider SDK types into the domain.
"""

from __future__ import annotations

from waywarden.services.approval_engine import ApprovalEngine
from waywarden.services.approval_types import (
    ApprovalAlreadyResolvedError,
    ApprovalDecision,
    DeniedAbandon,
    DeniedAlternatePath,
    Granted,
    Timeout,
)
from waywarden.services.context_builder import ContextBuilder

__all__ = [
    "ApprovalAlreadyResolvedError",
    "ApprovalDecision",
    "ApprovalEngine",
    "ContextBuilder",
    "DeniedAbandon",
    "DeniedAlternatePath",
    "Granted",
    "Timeout",
]
