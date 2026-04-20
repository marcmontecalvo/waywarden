"""NetworkPolicy — network access policy for the workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NetworkMode = Literal["deny", "allowlist", "profile-default"]
NetworkScheme = Literal["https", "http", "ssh", "tcp"]


@dataclass(frozen=True, slots=True)
class NetworkAllowRule:
    host_pattern: str
    purpose: str
    port: int | None = None
    scheme: NetworkScheme | None = None


@dataclass(frozen=True, slots=True)
class NetworkPolicy:
    mode: NetworkMode
    allow: list[NetworkAllowRule]
    deny: list[str]
