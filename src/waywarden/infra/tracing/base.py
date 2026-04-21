from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol, runtime_checkable


@runtime_checkable
class Span(Protocol):
    """Protocol that concrete span implementations must satisfy."""

    def set_attribute(self, key: str, value: str | int | float | bool) -> None: ...

    def add_event(
        self,
        name: str,
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> None: ...

    def record_exception(
        self,
        exception: Exception,
        *,
        attributes: dict[str, str | int | float | bool] | None = None,
        escaped: bool = False,
    ) -> None: ...


@runtime_checkable
class Tracer(Protocol):
    """Protocol that tracer backends must satisfy."""

    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> AbstractContextManager[Span]: ...
