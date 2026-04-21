import sys

from waywarden.infra.tracing.noop import NoopSpan, NoopTracer


def test_noop_does_not_import_otel() -> None:
    """NoopTracer must never import opentelemetry."""
    otel_modules = {k for k in sys.modules if "opentelemetry" in k}
    tracer = NoopTracer()
    span_ctx = tracer.start_span("test")
    _span = span_ctx.__enter__()
    span_ctx.__exit__(None, None, None)
    assert sys.modules.keys() - otel_modules == set() or all(
        "opentelemetry" not in k for k in sys.modules if k not in otel_modules
    )


def test_noop_span_ignores_all_calls() -> None:
    span = NoopSpan()
    span.set_attribute("key", "value")
    span.add_event("event")
    span.record_exception(RuntimeError("boom"))
