from __future__ import annotations

from contextlib import contextmanager
from typing import Any


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

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> Any:
        yield NoopSpan()
