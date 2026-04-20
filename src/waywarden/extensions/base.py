"""Typed extension base contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

ExtensionFactory = Callable[[Mapping[str, Any]], "Extension"]


@dataclass(frozen=True, slots=True)
class ExtensionDecl:
    """Startup-time declaration of an extension to be registered.

    Populated from profile packs or config; consumed by
    ``ExtensionRegistry.load_declared``.
    """

    name: str
    version: str
    capabilities: frozenset[str]
    config: Mapping[str, Any]
    factory: ExtensionFactory | None = None


class Extension(ABC):
    """Base contract for all Waywarden extensions.

    Subclasses must implement ``validate()``.  The registry calls this
    method at startup to reject bad configurations before the harness
    accepts the extension.
    """

    def __init__(
        self,
        name: str,
        version: str,
        capabilities: frozenset[str] | None = None,
    ) -> None:
        self.name = name
        self.version = version
        self.capabilities = capabilities or frozenset()

    @abstractmethod
    def validate(self, config: Mapping[str, Any]) -> None:
        """Validate the extension's configuration.

        Raise ``ExtensionConfigError`` (or a subclass) when the config
        is invalid.  Errors are aggregated by the registry and raised
        as a single ``ExtensionStartupError`` at startup.
        """
