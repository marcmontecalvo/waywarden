"""Channel adapter sub-package.

Exports concrete channel adapters and their base infrastructure.
"""

from __future__ import annotations

from waywarden.adapters.channel.base import ChannelAdapterBase
from waywarden.adapters.channel.errors import ChannelRejectedError, ChannelTransportError
from waywarden.adapters.channel.web import WebChannel

__all__ = [
    "ChannelAdapterBase",
    "ChannelRejectedError",
    "ChannelTransportError",
    "WebChannel",
]
