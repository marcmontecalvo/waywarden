"""Typed errors for the extension contract and registry."""

from __future__ import annotations


class ExtensionConfigError(ValueError):
    """Raised when an extension's validate() detects invalid configuration."""


class DuplicateExtensionError(KeyError):
    """Raised when registering an extension whose name already exists with a different version."""


class UnknownExtensionError(KeyError):
    """Raised when looking up an extension name that was never registered."""


class ExtensionStartupError(RuntimeError):
    """Aggregated failure raised when load_declared finds one or more validation errors."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(self.__str__())

    def __str__(self) -> str:
        lines = ["Extension startup failed:"]
        lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)
