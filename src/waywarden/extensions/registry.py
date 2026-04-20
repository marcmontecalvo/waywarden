"""Extension registry — startup-time validation and lookup."""

from __future__ import annotations

from waywarden.extensions.base import Extension, ExtensionDecl
from waywarden.extensions.errors import (
    DuplicateExtensionError,
    ExtensionConfigError,
    ExtensionStartupError,
    UnknownExtensionError,
)


class ExtensionRegistry:
    """Startup-time registry that validates and holds extensions.

    All operations are synchronous — the registry is consumed during
    harness initialisation before any async runtime is needed.
    """

    def __init__(self) -> None:
        self._extensions: dict[str, Extension] = {}

    def register(self, ext: Extension) -> None:
        """Register an extension by name.

        Idempotent when the same name and version are used.  Raises
        ``DuplicateExtensionError`` when a different version is supplied.
        """
        existing = self._extensions.get(ext.name)
        if existing is not None:
            if existing.version != ext.version:
                raise DuplicateExtensionError(
                    f"Extension {ext.name!r} already registered as version "
                    f"{existing.version!r}; cannot overwrite with {ext.version!r}"
                )
            # Same name + same version — idempotent no-op.
            return
        self._extensions[ext.name] = ext

    def get(self, name: str) -> Extension:
        """Return the extension with the given name.

        Raises ``UnknownExtensionError`` when the name is not found.
        """
        ext = self._extensions.get(name)
        if ext is None:
            raise UnknownExtensionError(
                f"Unknown extension {name!r}; registered extensions: {sorted(self._extensions)}"
            )
        return ext

    def load_declared(self, declared: list[ExtensionDecl]) -> None:
        """Validate and register a batch of declared extensions.

        Calls ``validate()`` on every declaration, aggregates all
        validation errors, and raises a single ``ExtensionStartupError``
        listing every failure.
        """
        errors: list[str] = []

        for decl in declared:
            try:
                ext = self._make_extension(decl)
                ext.validate(decl.config)
                self.register(ext)
            except ExtensionStartupError as exc:
                errors.extend(exc.errors)
            except ExtensionConfigError as exc:
                errors.append(f"{decl.name!r}: {exc}")
            except Exception as exc:
                errors.append(f"{decl.name!r}: unexpected error: {exc}")

        if errors:
            raise ExtensionStartupError(errors)

    def _make_extension(self, decl: ExtensionDecl) -> Extension:
        """Instantiate a concrete extension from a declaration.

        Subclasses may override to control instantiation strategy.
        """
        if decl.factory is not None:
            return decl.factory(decl.config)
        raise NotImplementedError(
            f"No factory provided for extension {decl.name!r}; "
            "subclasses must override _make_extension"
        )
