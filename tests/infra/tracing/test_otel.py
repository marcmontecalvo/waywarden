import pytest

pytest.importorskip("opentelemetry_api")
pytest.importorskip("opentelemetry_sdk")


def test_otel_records_span() -> None:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from waywarden.infra.tracing.otel import OtelTracer

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Install the provider so get_tracer picks it up.
    from opentelemetry import trace as trace_api

    trace_api.set_tracer_provider(provider)

    tracer = OtelTracer(name="test-otel")
    with tracer.start_span("hello", attributes={"key": "val"}):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "hello"
