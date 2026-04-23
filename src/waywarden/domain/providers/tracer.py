"""Tracer provider protocol.

Re-exports the ``Tracer`` / ``Span`` shapes from the infra tracing layer
under the provider namespace for consistency (ADR-0011).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from waywarden.infra.tracing.base import Tracer


@runtime_checkable
class TracerProvider(Protocol):
    """Protocol for tracer providers.

    The concrete adapter is the one from P2-12 (#47).
    """

    def get_tracer(self, name: str) -> Tracer: ...
