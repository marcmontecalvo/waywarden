"""Chat subcommand — single-message CLI client for the chat API.

Talks to the running API, renders RT-002 SSE events as they arrive, and
exits with an appropriate exit code based on the terminal event.

Uses ``httpx`` for HTTP/SSE and ``argparse`` for CLI framing.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping

import httpx

# Terminal event types and their exit codes.
_TERMINAL_EXIT_CODES: dict[str, int] = {
    "run.completed": 0,
    "run.failed": 1,
    "run.cancelled": 2,
}


def build_chat_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the ``chat`` subcommand to *subparsers*."""
    parser = subparsers.add_parser(
        "chat",
        help="Submit a message and stream the run's events to the terminal.",
    )
    parser.add_argument(
        "--server",
        default="http://127.0.0.1:8000",
        help="Base URL of the Waywarden API server.",
    )
    parser.add_argument(
        "--session",
        default="default",
        help="Session identifier (maps to profile/run context).",
    )
    parser.add_argument(
        "--message",
        required=True,
        help="Message to submit to the chat API.",
    )
    parser.add_argument(
        "--last-seen-seq",
        type=int,
        default=0,
        help="Resume SSE stream from this sequence number.",
    )
    parser.set_defaults(handler=_handle_chat)


def _handle_chat(args: argparse.Namespace) -> int:
    """Execute the chat subcommand.

    1. POST to ``{server}/chat`` with the message.
    2. Subscribe to the SSE stream at the returned ``stream_url``.
    3. Render each event as ``seq <type> <id>: <payload>``.
    4. On a terminal event, print a summary and exit with the code
       from ``_TERMINAL_EXIT_CODES``.

    Returns
    -------
    int
        0 for completed, 1 for failed, 2 for cancelled, 3 for error.
    """
    server = args.server.rstrip("/")
    session = args.session
    message = args.message
    last_seq = args.last_seen_seq

    try:
        with httpx.Client(timeout=30.0) as client:
            # --- POST /chat ---
            resp = client.post(
                f"{server}/chat",
                json={"session_id": session, "message": message},
                headers={"X-Waywarden-Operator": "cli"},
            )
            resp.raise_for_status()
            body = resp.json()
            run_id = body["run_id"]
            stream_url = body["stream_url"]

            print(f"[run] {run_id}", file=sys.stderr)

            # --- GET SSE stream ---
            # Append last_seen_seq for resume semantics
            if last_seq > 0:
                sep = "&" if "?" in stream_url else "?"
                stream_url = f"{stream_url}{sep}last_seen_seq={last_seq}"
            resp = client.get(stream_url)
            resp.raise_for_status()

            exit_code = 3  # default: unknown error

            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8") if isinstance(line, bytes) else str(line)
                if not decoded.startswith("data: "):
                    continue

                try:
                    event = json.loads(decoded[len("data: ") :])
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type", "unknown")
                event_seq = event.get("seq", "?")
                summary = _format_event(event)

                print(f"[{event_seq}] {event_type}: {summary}")

                # Terminal event?
                if event_type in _TERMINAL_EXIT_CODES:
                    exit_code = _TERMINAL_EXIT_CODES[event_type]
                    break

            # Progress report
            print(f"{run_id} finished", file=sys.stderr)

    except httpx.RequestError as exc:
        print(f"Error: could not reach {server} — {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3

    return exit_code


def _payload_map(event: Mapping[str, object]) -> Mapping[str, object]:
    payload = event.get("payload", {})
    if isinstance(payload, Mapping):
        return payload
    return {}


def _string_field(mapping: Mapping[str, object], key: str, default: str = "") -> str:
    value = mapping.get(key, default)
    return value if isinstance(value, str) else default


def _format_event(event: Mapping[str, object]) -> str:
    """Render an SSE event as a short human-readable summary."""
    event_type = _string_field(event, "type", "unknown")
    if event_type == "run.created":
        return f"profile={_string_field(_payload_map(event), 'profile', '?')}"
    if event_type == "run.progress":
        payload = _payload_map(event)
        return f"{_string_field(payload, 'phase', '?')}/{_string_field(payload, 'milestone', '?')}"
    if event_type == "run.completed":
        return _string_field(_payload_map(event), "outcome", "ok")
    if event_type == "run.failed":
        payload = _payload_map(event)
        fc = _string_field(payload, "failure_code", "error")
        msg = _string_field(payload, "message", "")
        return f"{fc}: {msg}"
    if event_type == "run.cancelled":
        return _string_field(_payload_map(event), "reason", "unknown")
    if event_type == "run.artifact_created":
        return _string_field(_payload_map(event), "artifact_kind", "?")
    if event_type == "run.plan_ready":
        return _string_field(_payload_map(event), "summary", "")
    if event_type == "run.execution_started":
        return _string_field(_payload_map(event), "worker_session_ref", "")
    if event_type == "run.approval_waiting":
        return _string_field(_payload_map(event), "approval_kind", "")
    if event_type == "run.resumed":
        return _string_field(_payload_map(event), "resume_kind", "")
    return ""
