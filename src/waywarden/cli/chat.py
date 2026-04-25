"""Chat subcommand — single-message CLI client for the chat API.

Talks to the running API, renders RT-002 SSE events as they arrive, and
exits with an appropriate exit code based on the terminal event.

Uses ``httpx`` for HTTP/SSE and ``argparse`` for CLI framing.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import httpx

# Terminal event types and their exit codes.
_TERMINAL_EXIT_CODES: dict[str, int] = {
    "run.completed": 0,
    "run.failed": 1,
    "run.cancelled": 2,
}

def build_chat_parser(subparsers: Any) -> None:  # type: ignore[type-arg]
    """Add the ``chat`` subcommand to *subparsers*."""
    parser = subparsers.add_parser(  # type: ignore[attr-defined]
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
    parser.set_defaults(handler=_handle_chat)  # type: ignore[attr-defined]


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
                decoded = line.decode("utf-8") if isinstance(line, bytes) else line  # type: ignore[union-attr]
                if not decoded.startswith("data: "):
                    continue

                try:
                    event = json.loads(decoded[len("data: "):])
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


def _format_event(event: Any) -> str:
    """Render an SSE event as a short human-readable summary."""
    event_type = event.get("type", "unknown")
    if event_type == "run.created":
        return f"profile={event.get('payload', {}).get('profile', '?')}"
    elif event_type == "run.progress":
        p = event.get("payload", {})
        return f"{p.get('phase', '?')}/{p.get('milestone', '?')}"
    elif event_type == "run.completed":
        return event.get("payload", {}).get("outcome", "ok")
    elif event_type == "run.failed":
        fc = event.get('payload', {}).get('failure_code', 'error')
        msg = event.get('payload', {}).get('message', '')
        return f"{fc}: {msg}"
    elif event_type == "run.cancelled":
        return event.get("payload", {}).get("reason", "unknown")
    elif event_type == "run.artifact_created":
        return f"{event.get('payload', {}).get('artifact_kind', '?')}"
    elif event_type == "run.plan_ready":
        return event.get("payload", {}).get("summary", "")
    elif event_type == "run.execution_started":
        return event.get("payload", {}).get("worker_session_ref", "")
    elif event_type == "run.approval_waiting":
        return event.get("payload", {}).get("approval_kind", "")
    elif event_type == "run.resumed":
        return event.get("payload", {}).get("resume_kind", "")
    return ""
