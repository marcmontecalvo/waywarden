"""Test that all provider protocols are @runtime_checkable."""

from __future__ import annotations

import pytest

from waywarden.domain.providers import (
    ChannelProvider,
    KnowledgeProvider,
    MemoryProvider,
    ModelProvider,
    ToolProvider,
    TracerProvider,
)


@pytest.mark.asyncio
async def test_all_protocols_runtime_checkable() -> None:
    """Every Protocol must be @runtime_checkable so that isinstance checks
    work at startup without importing provider SDKs."""
    for proto in (
        ModelProvider,
        MemoryProvider,
        KnowledgeProvider,
        ToolProvider,
        ChannelProvider,
        TracerProvider,
    ):
        # Verify the class is a Protocol subclass
        assert hasattr(proto, "__protocol_attrs__") or hasattr(
            proto, "__protocol__"
        ), f"{proto.__name__} should be a Protocol"
        # Verify it is marked runtime_checkable via the internal flag
        assert getattr(proto, "_is_runtime_protocol", False), (
            f"{proto.__name__} must be @runtime_checkable"
        )
