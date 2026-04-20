"""SecretScope — secret exposure policy for the workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SecretMode = Literal["none", "brokered", "env-mounted"]
RedactionLevel = Literal["full", "names-only", "none"]


@dataclass(frozen=True, slots=True)
class SecretScope:
    mode: SecretMode
    allowed_secret_refs: list[str]
    mount_env: list[str]
    redaction_level: RedactionLevel = "full"
