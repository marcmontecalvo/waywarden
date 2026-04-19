"""Shared opaque identifier types for provider-neutral domain models."""

from typing import NewType

InstanceId = NewType("InstanceId", str)
SessionId = NewType("SessionId", str)
MessageId = NewType("MessageId", str)
