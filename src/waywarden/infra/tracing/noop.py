from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any

from waywarden.infra.tracing.base import Span


class NoopSpan:
    """No-op span that silently ignores all operations."""

    __slots__ = ()

    def set_attribute(self, key: str, value: str | int | float | bool) -> None:
        pass

    def add_event(
        self,
        name: str,
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        pass

    def record_exception(
        self,
        exception: Exception,
        *,
        attributes: dict[str, str | int | float | bool] | None = None,
        escaped: bool = False,
    ) -> None:
        pass


class NoopTracer:
    """Zero-cost tracer that never imports opentelemetry."""

    __slots__ = ()

    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> AbstractContextManager[Span]:
        return _NoopSpanContext()


class _NoopSpanContext(AbstractContextManager[Span]):
    __slots__ = ("_span",)

    def __init__(self) -> None:
        self._span = NoopSpan()

    def __enter__(self) -> Span:
        return self._span

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        pass
