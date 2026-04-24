"""Channel binding types for Instance configuration.

A ChannelBinding declares how an instance exposes itself through a specific
transport.  Bindings are validated at startup against the set of known
transports and duplicate (transport, path) pairs are rejected.

See ADR-0002 (adapter boundary) and ADR-0011 (harness boundaries).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

__all__ = ["ChannelBinding", "ChannelTransport"]

ChannelTransport = Literal["http", "sse", "cli"]

_VALID_TRANSports: set[str] = {"http", "sse", "cli"}

# Registry of known channel names.  Populated by ChannelProvider implementations.
# When non-empty, channel names on instances must match a registered provider.
_CHANNEL_REGISTRY: set[str] = set()


def register_channel_provider(name: str) -> None:
    """Register a channel provider name so its instances can be referenced.

    Called by concrete ChannelProvider adapters (e.g. web channel, CLI channel)
    at import time.  The registry starts empty until adapters are implemented.
    """
    _CHANNEL_REGISTRY.add(name)


def get_channel_registry() -> frozenset[str]:
    """Return a snapshot of registered channel provider names."""
    return frozenset(_CHANNEL_REGISTRY)


@dataclass(frozen=True, slots=True)
class ChannelBinding:
    """Declares how an instance binds to a channel transport.

    Parameters
    ----------
    channel_name:
        Human-readable name of the channel binding.
    transport:
        One of ``http``, ``sse``, or ``cli``.
    path:
        Optional endpoint path (e.g. ``/api/chat``).  ``None`` for transports
        that do not use paths.
    enabled:
        When ``False`` the binding is silently skipped at startup.  Defaults
        to ``True``.
    """

    channel_name: str = field(compare=True)
    transport: ChannelTransport = field(compare=True)
    path: str | None = field(default=None, compare=True)
    enabled: bool = field(default=True, compare=True)

    def __post_init__(self) -> None:
        trimmed = self.channel_name.strip()
        if not trimmed:
            raise ValueError("channel_name must not be blank")
        object.__setattr__(self, "channel_name", trimmed)

        if self.transport not in _VALID_TRANSports:
            raise ValueError(
                f"transport must be one of {sorted(_VALID_TRANSports)}, got {self.transport!r}"
            )
