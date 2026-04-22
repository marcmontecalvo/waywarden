"""Tests for the extension registry."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from waywarden.extensions.base import Extension, ExtensionDecl
from waywarden.extensions.errors import (
    DuplicateExtensionError,
    ExtensionConfigError,
    ExtensionStartupError,
    UnknownExtensionError,
)
from waywarden.extensions.registry import ExtensionRegistry


class _TestExt(Extension):
    def __init__(self, name: str, version: str, fail: bool = False) -> None:
        super().__init__(name=name, version=version)
        self.fail = fail

    def validate(self, config: Mapping[str, object]) -> None:
        if self.fail:
            raise ExtensionConfigError("validation failed")


def _make_ext(name: str, version: str = "1.0.0", fail: bool = False):
    return lambda _config: _TestExt(name=name, version=version, fail=fail)


def _decl(name: str, version: str = "1.0.0", fail: bool = False) -> ExtensionDecl:
    return ExtensionDecl(
        name=name,
        version=version,
        capabilities=frozenset(),
        config={},
        factory=_make_ext(name, version, fail),
    )


# --- register ---


def test_duplicate_name_different_version_rejected() -> None:
    reg = ExtensionRegistry()
    ext_a = _TestExt(name="foo", version="1.0.0")
    ext_b = _TestExt(name="foo", version="2.0.0")
    reg.register(ext_a)
    with pytest.raises(DuplicateExtensionError, match="cannot overwrite"):
        reg.register(ext_b)


def test_duplicate_extension_error_is_not_key_error() -> None:
    """DuplicateExtensionError must not subclass KeyError — it is a conflict, not a missing key."""
    assert not issubclass(DuplicateExtensionError, KeyError)
    assert isinstance(DuplicateExtensionError("test"), Exception)


def test_duplicate_name_same_version_idempotent() -> None:
    reg = ExtensionRegistry()
    ext = _TestExt(name="foo", version="1.0.0")
    reg.register(ext)
    reg.register(ext)  # no-op, should not raise
    assert reg.get("foo") is ext


def test_unknown_extension_raises() -> None:
    reg = ExtensionRegistry()
    with pytest.raises(UnknownExtensionError, match="Unknown extension"):
        reg.get("nonexistent")


# --- load_declared ---


def test_load_declared_aggregates_errors() -> None:
    reg = ExtensionRegistry()
    decl_a = _decl("bad-a", fail=True)
    decl_b = _decl("bad-b", fail=True)
    with pytest.raises(ExtensionStartupError) as exc_info:
        reg.load_declared([decl_a, decl_b])
    assert len(exc_info.value.errors) == 2
    assert "bad-a" in exc_info.value.errors[0]
    assert "bad-b" in exc_info.value.errors[1]


def test_load_declared_succeeds_when_all_valid() -> None:
    reg = ExtensionRegistry()
    decl_a = _decl("good-a")
    decl_b = _decl("good-b")
    reg.load_declared([decl_a, decl_b])
    assert reg.get("good-a").name == "good-a"
    assert reg.get("good-b").name == "good-b"
