from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from opentelemetry.trace import get_tracer
from opentelemetry.trace.span import Span as OtelSpan


class _OtelSpanBridge:
    """Bridge OTel span to our Span protocol."""

    __slots__ = ("_span",)

    def __init__(self, span: OtelSpan) -> None:
        self._span = span

    def set_attribute(self, key: str, value: str | int | float | bool) -> None:
        self._span.set_attribute(key, value)

    def add_event(
        self,
        name: str,
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"name": name}
        if attributes is not None:
            kwargs["attributes"] = attributes
        self._span.add_event(**kwargs)

    def record_exception(
        self,
        exception: Exception,
        *,
        attributes: dict[str, str | int | float | bool] | None = None,
        escaped: bool = False,
    ) -> None:
        self._span.record_exception(exception, escaped=escaped, attributes=attributes)

    def end(self) -> None:
        self._span.end()


class OtelTracer:
    """OpenTelemetry-backed tracer.

    OTel imports happen only when this class is instantiated, so callers
    that use NoopTracer never pay the import cost.
    """

    __slots__ = ("_tracer",)

    def __init__(
        self,
        name: str = "waywarden",
        version: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        if endpoint:
            # Minimal OTel setup: configure the SDK only when an endpoint is given.
            try:
                from opentelemetry.sdk.trace.export import (  # noqa: E501, I001
                    ConsoleSpanExporter,
                )

                from opentelemetry.sdk.trace import TracerProvider  # noqa: I001

                from opentelemetry import trace as trace_api

                provider = TracerProvider()
                provider.add_span_processor(
                    # pyright: ignore[reportAttributeAccessIssue]
                    __import__(
                        "opentelemetry.sdk.trace.export", fromlist=["SimpleSpanProcessor"]
                    ).SimpleSpanProcessor(ConsoleSpanExporter())
                )
                # pyright: ignore[reportPossiblyUnboundVariable]
                trace_api.set_tracer_provider(provider)
            except ImportError as err:
                raise RuntimeError(
                    "OTel SDK not fully available: the API is installed but the SDK is not. "
                    "Install opentelemetry-sdk to enable tracing."
                ) from err

        self._tracer = get_tracer(name, version)

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {"name": name}
        if attributes is not None:
            kwargs["attributes"] = attributes
        otel_span = self._tracer.start_span(**kwargs)
        bridge = _OtelSpanBridge(otel_span)
        try:
            yield bridge
        finally:
            bridge.end()
