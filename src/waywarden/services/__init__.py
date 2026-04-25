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
from waywarden.services.resume import ResumeService
from waywarden.services.resume_errors import (
    CrossRunCheckpointError,
    ManifestChangedWithoutRevisionError,
    ResumeServiceError,
)

__all__ = [
    "ApprovalAlreadyResolvedError",
    "ApprovalDecision",
    "ApprovalEngine",
    "ContextBuilder",
    "CrossRunCheckpointError",
    "DeniedAbandon",
    "DeniedAlternatePath",
    "Granted",
    "ManifestChangedWithoutRevisionError",
    "ResumeService",
    "ResumeServiceError",
    "Timeout",
]
