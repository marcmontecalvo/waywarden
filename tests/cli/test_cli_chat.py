"""Tests for the CLI chat subcommand."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from waywarden.cli.chat import _format_event, _handle_chat

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iter_sse_lines(events: list[dict[str, Any]]) -> Any:
    """Make an iterator that yields individual SSE lines (split, not frames)."""
    lines: list[bytes] = []
    for ev in events:
        frame = f"id: {ev.get('seq', 0)}\ndata: {json.dumps(ev)}\n\n\n"
        for raw_line in frame.strip("\n\n\n").split("\n"):
            lines.append(raw_line.encode())
        lines.append(b"")  # blank line separator
    lines.append(b"")  # final blank line
    return iter(lines)


# ---------------------------------------------------------------------------
# Test: happy path exits zero
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_happy_path_exit_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI returns exit code 0 for a run.completed terminal event."""
    run_id = "run-abc123"
    created = {
        "run_id": run_id,
        "stream_url": f"http://127.0.0.1:8000/runs/{run_id}/events?last_seen_seq=0",
    }

    stream_events = [
        {"seq": 1, "type": "run.created", "payload": {"profile": "ea"}},
        {
            "seq": 2,
            "type": "run.progress",
            "payload": {"phase": "intake", "milestone": "received"},
        },
        {"seq": 3, "type": "run.completed", "payload": {"outcome": "ok"}},
    ]

    captured_url: dict[str, str] = {"url": ""}

    resp_created = MagicMock(spec=httpx.Response)
    resp_created.status_code = 202
    resp_created.json.return_value = created
    resp_created.raise_for_status.return_value = None
    resp_created.iter_lines.return_value = iter([])

    resp_stream = MagicMock(spec=httpx.Response)
    resp_stream.status_code = 200
    resp_stream.raise_for_status.return_value = None
    resp_stream.iter_lines.return_value = _iter_sse_lines(stream_events)

    def fake_post(self: httpx.Client, *args: Any, **kwargs: Any) -> httpx.Response:  # type: ignore[reportUnknownParameterType]
        return resp_created  # type: ignore[return-value]

    def fake_get(self: httpx.Client, *args: Any, **kwargs: Any) -> httpx.Response:  # type: ignore[reportUnknownParameterType]
        captured = kwargs.get("url", args[0] if args else "")
        captured_url["url"] = captured
        return resp_stream  # type: ignore[return-value]

    with patch.object(httpx.Client, "post", fake_post):
        with patch.object(httpx.Client, "get", fake_get):
            args = MagicMock()
            args.server = "http://127.0.0.1:8000"
            args.session = "test"
            args.message = "hello"
            args.last_seen_seq = 0

            exit_code = _handle_chat(args)

    assert exit_code == 0


# ---------------------------------------------------------------------------
# Test: failed run exits one
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_failed_run_exit_one(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ARG001
    """CLI returns exit code 1 for a run.failed terminal event."""
    stream_events = [
        {"seq": 1, "type": "run.created", "payload": {"profile": "ea"}},
        {
            "seq": 2,
            "type": "run.failed",
            "payload": {"failure_code": "TOOL_ERROR", "message": "boom", "retryable": False},
        },
    ]

    resp_created = MagicMock(spec=httpx.Response)
    resp_created.status_code = 202
    resp_created.json.return_value = {"run_id": "run-x", "stream_url": "/routes"}
    resp_created.raise_for_status.return_value = None
    resp_created.iter_lines.return_value = iter([])

    resp_stream = MagicMock(spec=httpx.Response)
    resp_stream.status_code = 200
    resp_stream.raise_for_status.return_value = None
    resp_stream.iter_lines.return_value = _iter_sse_lines(stream_events)

    def fake_post(self: httpx.Client, *args: Any, **kwargs: Any) -> httpx.Response:  # type: ignore[reportUnknownParameterType]
        return resp_created  # type: ignore[return-value]

    def fake_get(self: httpx.Client, *args: Any, **kwargs: Any) -> httpx.Response:  # type: ignore[reportUnknownParameterType]
        return resp_stream  # type: ignore[return-value]

    with patch.object(httpx.Client, "post", fake_post):
        with patch.object(httpx.Client, "get", fake_get):
            args = MagicMock()
            args.server = "http://127.0.0.1:8000"
            args.session = "test"
            args.message = "test"
            args.last_seen_seq = 0

            assert _handle_chat(args) == 1


# ---------------------------------------------------------------------------
# Test: cancelled run exits two
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_cancelled_run_exit_two(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ARG001
    """CLI returns exit code 2 for a run.cancelled terminal event."""
    stream_events = [
        {"seq": 1, "type": "run.created", "payload": {"profile": "ea"}},
        {"seq": 2, "type": "run.cancelled", "payload": {"reason": "user_aborted"}},
    ]

    resp_created = MagicMock(spec=httpx.Response)
    resp_created.status_code = 202
    resp_created.json.return_value = {"run_id": "run-x", "stream_url": "/routes"}
    resp_created.raise_for_status.return_value = None
    resp_created.iter_lines.return_value = iter([])

    resp_stream = MagicMock(spec=httpx.Response)
    resp_stream.status_code = 200
    resp_stream.raise_for_status.return_value = None
    resp_stream.iter_lines.return_value = _iter_sse_lines(stream_events)

    def fake_post(self: httpx.Client, *args: Any, **kwargs: Any) -> httpx.Response:  # type: ignore[reportUnknownParameterType]
        return resp_created  # type: ignore[return-value]

    def fake_get(self: httpx.Client, *args: Any, **kwargs: Any) -> httpx.Response:  # type: ignore[reportUnknownParameterType]
        return resp_stream  # type: ignore[return-value]

    with patch.object(httpx.Client, "post", fake_post):
        with patch.object(httpx.Client, "get", fake_get):
            args = MagicMock()
            args.server = "http://127.0.0.1:8000"
            args.session = "test"
            args.message = "test"
            args.last_seen_seq = 0

            assert _handle_chat(args) == 2


# ---------------------------------------------------------------------------
# Test: last_seen_seq resumes from N
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_last_seen_seq_resumes(monkeypatch: pytest.MonkeyPatch) -> None:
    """--last-seen-seq N is passed as a query parameter in the stream URL."""
    captured_url: dict[str, str] = {"url": ""}

    resp_created = MagicMock(spec=httpx.Response)
    resp_created.status_code = 202
    resp_created.json.return_value = {"run_id": "run-x", "stream_url": "/routes"}
    resp_created.raise_for_status.return_value = None
    resp_created.iter_lines.return_value = iter([])

    def fake_get(self: httpx.Client, *args: Any, **kwargs: Any) -> httpx.Response:  # type: ignore[reportUnknownParameterType]
        captured_url["url"] = kwargs.get("url", args[0] if args else "")
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.iter_lines.return_value = iter([])
        return resp  # type: ignore[return-value]

    def fake_post(self: httpx.Client, *args: Any, **kwargs: Any) -> httpx.Response:  # type: ignore[reportUnknownParameterType]
        return resp_created  # type: ignore[return-value]

    with patch.object(httpx.Client, "post", fake_post):
        with patch.object(httpx.Client, "get", fake_get):
            args = MagicMock()
            args.server = "http://127.0.0.1:8000"
            args.session = "test"
            args.message = "test"
            args.last_seen_seq = 42

            _handle_chat(args)

    assert "last_seen_seq=42" in captured_url["url"]


# ---------------------------------------------------------------------------
# Test: unreachable server exits non-zero
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_unreachable_server_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI prints error and exits non-zero when server is unreachable."""

    def fake_post(self: httpx.Client, *args: Any, **kwargs: Any) -> None:  # type: ignore[reportUnknownParameterType]
        raise httpx.ConnectError("Connection refused")

    with patch.object(httpx.Client, "post", fake_post):
        args = MagicMock()
        args.server = "http://10.255.255.1:9999"
        args.session = "test"
        args.message = "test"
        args.last_seen_seq = 0

        assert _handle_chat(args) == 3


# ---------------------------------------------------------------------------
# Test: build_parser adds chat subcommand
# ---------------------------------------------------------------------------


def test_build_parser_adds_chat_subcommand() -> None:
    """The chat command is registered as a subcommand."""
    from waywarden.cli.main import build_parser

    parser = build_parser()
    args = parser.parse_args(["chat", "--message", "hello"])
    assert args.command == "chat"
    assert args.message == "hello"
    assert args.server == "http://127.0.0.1:8000"
    assert args.session == "default"
    assert args.last_seen_seq == 0


# ---------------------------------------------------------------------------
# Test: _format_event renders event types
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_format_event_rendered_correctly() -> None:  # noqa: ANN201
    """_format_event returns sensible summaries for known event types."""
    assert _format_event({"type": "run.created", "payload": {"profile": "ea"}}) == "profile=ea"
    assert (
        _format_event(
            {
                "type": "run.progress",
                "payload": {"phase": "plan", "milestone": "ready"},
            }
        )
        == "plan/ready"
    )
    assert _format_event({"type": "run.completed", "payload": {"outcome": "ok"}}) == "ok"
    assert (
        _format_event(
            {
                "type": "run.failed",
                "payload": {"failure_code": "E1", "message": "fail"},
            }
        )
        == "E1: fail"
    )
    assert _format_event({"type": "run.cancelled", "payload": {"reason": "abort"}}) == "abort"
    assert (
        _format_event({"type": "run.artifact_created", "payload": {"artifact_kind": "ps"}}) == "ps"
    )
