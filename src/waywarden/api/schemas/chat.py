"""Chat API schema types.

Pydantic v2 models at the API boundary; domain objects stay internal.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """Incoming chat message payload.

    Parameters
    ----------
    session_id:
        Stable session identifier.
    message:
        The user's message text.
    manifest_ref:
        Optional workspace manifest reference.
    policy_preset:
        Optional policy preset override.
    """

    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    manifest_ref: str | None = None
    policy_preset: str | None = None


class ChatResponse(BaseModel):
    """Immediate response to a chat POST.

    Parameters
    ----------
    run_id:
        The run that was created for this message.
    stream_url:
        SSE endpoint URL with last_seen_seq=0.
    """

    run_id: str
    stream_url: str
