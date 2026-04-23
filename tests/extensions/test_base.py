"""Tests for the extension base contract."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from waywarden.extensions.base import Extension
from waywarden.extensions.errors import ExtensionConfigError


class _ConcreteExtension(Extension):
    def validate(self, config: Mapping[str, object]) -> None:
        pass


def test_subclass_without_validate_is_abstract() -> None:
    """Omitting validate() makes the class abstract and uninstantiable."""

    class BadExtension(Extension):
        pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BadExtension(name="bad", version="1.0.0")  # type: ignore[abstract]


def test_concrete_extension_instantiates() -> None:
    ext = _ConcreteExtension(name="test", version="1.0.0")
    assert ext.name == "test"
    assert ext.version == "1.0.0"
    assert ext.capabilities == frozenset()


def test_concrete_extension_with_capabilities() -> None:
    caps = frozenset(["read", "write"])
    ext = _ConcreteExtension(name="test", version="1.0.0", capabilities=caps)
    assert ext.capabilities == caps


def test_validate_raises_extension_config_error() -> None:
    class FailingExtension(Extension):
        def validate(self, config: Mapping[str, object]) -> None:
            raise ExtensionConfigError("bad config")

    ext = FailingExtension(name="fail", version="1.0.0")
    with pytest.raises(ExtensionConfigError, match="bad config"):
        ext.validate({})
