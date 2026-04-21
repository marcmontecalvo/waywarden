from __future__ import annotations

from waywarden.config.settings import AppConfig
from waywarden.infra.tracing.base import Tracer
from waywarden.infra.tracing.noop import NoopTracer


def build_tracer(cfg: AppConfig) -> Tracer:
    """Build a Tracer based on AppConfig.tracer setting."""
    mode = cfg.tracer
    if mode == "otel":
        from waywarden.infra.tracing.otel import OtelTracer

        return OtelTracer(endpoint=cfg.tracer_endpoint)
    return NoopTracer()
