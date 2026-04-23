import io
import json
from contextlib import redirect_stderr
from uuid import UUID

from fastapi.testclient import TestClient
from httpx import Response

from waywarden.app import create_app
from waywarden.config import AppConfig
from waywarden.logging import (
    RequestLogContext,
    configure_logging,
    get_logger,
    request_log_context,
)


def test_json_log_shape() -> None:
    stderr = io.StringIO()
    configure_logging(level="DEBUG", stream=stderr)
    logger = get_logger("waywarden.test")

    with request_log_context(
        RequestLogContext(
            request_id="f2f6c84e-45fe-4cb7-8850-205d40ba7ca8",
            client_request_id="client.req-1234",
        )
    ):
        logger.info("shape.check")

    payload = json.loads(stderr.getvalue().strip())
    assert payload["ts"]
    assert payload["level"] == "INFO"
    assert payload["msg"] == "shape.check"
    assert payload["request_id"] == "f2f6c84e-45fe-4cb7-8850-205d40ba7ca8"
    assert payload["logger"] == "waywarden.test"
    assert payload["client_request_id"] == "client.req-1234"


def test_healthz_logs_start_and_end_with_server_generated_request_id() -> None:
    response, logs = _call_healthz()

    started = _find_log(logs, "request.started")
    completed = _find_log(logs, "request.completed")
    response_request_id = response.headers["X-Request-ID"]

    assert response.status_code == 200
    assert UUID(response_request_id).version == 4
    assert started["request_id"] == response_request_id
    assert completed["request_id"] == response_request_id
    assert "client_request_id" not in started
    assert "client_request_id" not in completed


def test_malformed_client_request_id_is_ignored() -> None:
    response, logs = _call_healthz(headers={"X-Request-ID": "short"})

    started = _find_log(logs, "request.started")
    response_request_id = response.headers["X-Request-ID"]

    assert UUID(response_request_id).version == 4
    assert started["request_id"] == response_request_id
    assert "client_request_id" not in started


def test_well_formed_client_request_id_is_secondary_only() -> None:
    client_request_id = "client.req-1234"
    response, logs = _call_healthz(headers={"X-Request-ID": client_request_id})

    started = _find_log(logs, "request.started")
    completed = _find_log(logs, "request.completed")
    response_request_id = response.headers["X-Request-ID"]

    assert UUID(response_request_id).version == 4
    assert started["request_id"] == response_request_id
    assert completed["request_id"] == response_request_id
    assert started["client_request_id"] == client_request_id
    assert completed["client_request_id"] == client_request_id
    assert started["request_id"] != client_request_id


def _call_healthz(
    headers: dict[str, str] | None = None,
) -> tuple[Response, list[dict[str, object]]]:
    stderr = io.StringIO()
    settings = AppConfig(host="127.0.0.1", port=9001, active_profile="ea", log_level="INFO")

    with redirect_stderr(stderr):
        client = TestClient(create_app(settings))
        response = client.get("/healthz", headers=headers or {})

    logs = [json.loads(line) for line in stderr.getvalue().splitlines() if line.strip()]
    return response, logs


def _find_log(logs: list[dict[str, object]], message: str) -> dict[str, object]:
    for log in logs:
        if log.get("msg") == message:
            return log
    raise AssertionError(f"missing log message: {message}")
