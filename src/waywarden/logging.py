from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import IO
from uuid import uuid4

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")
_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_client_request_id_var: ContextVar[str | None] = ContextVar(
    "client_request_id",
    default=None,
)


@dataclass(frozen=True)
class RequestLogContext:
    request_id: str
    client_request_id: str | None


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        record.client_request_id = _client_request_id_var.get()
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object | None] = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "logger": record.name,
        }
        client_request_id = getattr(record, "client_request_id", None)
        if client_request_id is not None:
            payload["client_request_id"] = client_request_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: str = "INFO", stream: IO[str] | None = None) -> None:
    root_logger = logging.getLogger()
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(RequestContextFilter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def build_request_log_context(client_request_id: str | None) -> RequestLogContext:
    sanitized_client_request_id = (
        client_request_id
        if client_request_id is not None
        and _REQUEST_ID_PATTERN.fullmatch(client_request_id) is not None
        else None
    )
    return RequestLogContext(
        request_id=str(uuid4()),
        client_request_id=sanitized_client_request_id,
    )


@contextmanager
def request_log_context(context: RequestLogContext) -> Iterator[None]:
    request_token: Token[str | None] = _request_id_var.set(context.request_id)
    client_token: Token[str | None] = _client_request_id_var.set(context.client_request_id)
    try:
        yield
    finally:
        _request_id_var.reset(request_token)
        _client_request_id_var.reset(client_token)
