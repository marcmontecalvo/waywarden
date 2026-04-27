"""Utility for computing manifest content hashes.

Used by the resume service to detect manifest drift between run creation
and crash-resume scenarios.
"""

from __future__ import annotations

import hashlib


def content_hash(body: str) -> str:
    """Return a SHA-256 hex digest of ``body``.

    Parameters
    ----------
    body:
        The raw string representation of a manifest blob.

    Returns
    -------
    A 64-character hex string.
    """
    raw = body.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
