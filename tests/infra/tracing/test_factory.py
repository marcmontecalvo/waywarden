import pytest

from waywarden.config.settings import AppConfig
from waywarden.infra.tracing.factory import build_tracer
from waywarden.infra.tracing.noop import NoopTracer


def test_factory_returns_noop_by_default() -> None:
    cfg = AppConfig(host="localhost", port=8080, active_profile="ea")
    tracer = build_tracer(cfg)
    assert isinstance(tracer, NoopTracer)


def test_factory_returns_noop_when_explicitly_set() -> None:
    cfg = AppConfig(host="localhost", port=8080, active_profile="ea", tracer="noop")
    tracer = build_tracer(cfg)
    assert isinstance(tracer, NoopTracer)


def test_factory_dispatches_otel_when_endpoint_provided() -> None:
    """Factory should attempt OtelTracer when tracer='otel' and endpoint is set.

    OTel is not installed in the base dev environment, so the lazy import of
    OtelTracer fails with ImportError/ModuleNotFoundError.
    """
    cfg = AppConfig(
        host="localhost",
        port=8080,
        active_profile="ea",
        tracer="otel",
        tracer_endpoint="http://localhost:4317",
    )
    with pytest.raises((ImportError, ModuleNotFoundError)):
        build_tracer(cfg)
