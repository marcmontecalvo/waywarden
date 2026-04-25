from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import cast

import uvicorn

from waywarden.app import create_app
from waywarden.cli.chat import build_chat_parser
from waywarden.config import ConfigLoadError, InstanceLoadError, load_app_config, load_instances
from waywarden.profiles import ProfileLoadError, load_profiles

type CommandHandler = Callable[[argparse.Namespace], int]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="waywarden",
        description="Waywarden harness CLI for the M1 boot slice.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the FastAPI app using the configured host and port.",
    )
    serve_parser.set_defaults(handler=_handle_serve)

    list_profiles_parser = subparsers.add_parser(
        "list-profiles",
        help="List checked-in profile fixtures.",
    )
    list_profiles_parser.set_defaults(handler=_handle_list_profiles)

    list_instances_parser = subparsers.add_parser(
        "list-instances",
        help="List checked-in instance fixtures.",
    )
    list_instances_parser.set_defaults(handler=_handle_list_instances)

    build_chat_parser(subparsers)

    return parser


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    handler = cast("CommandHandler", args.handler)

    try:
        return handler(args)
    except (ConfigLoadError, InstanceLoadError, ProfileLoadError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _handle_serve(_args: argparse.Namespace) -> int:
    settings = load_app_config()
    app = create_app(settings)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    return 0


def _handle_list_profiles(_args: argparse.Namespace) -> int:
    registry = load_profiles()
    print("id\tdisplay_name\tversion")
    for descriptor in registry.values():
        print(f"{descriptor.id}\t{descriptor.display_name}\t{descriptor.version}")
    return 0


def _handle_list_instances(_args: argparse.Namespace) -> int:
    registry = load_instances()
    print("id\tdisplay_name\tprofile_id\tconfig_path")
    for descriptor in registry.values():
        print(
            f"{descriptor.id}\t{descriptor.display_name}\t{descriptor.profile_id}\t"
            f"{descriptor.config_path.as_posix()}"
        )
    return 0
