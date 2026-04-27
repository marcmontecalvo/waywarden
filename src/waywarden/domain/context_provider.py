"""Repo-aware context provider for coding sessions.

Provides git metadata, filesystem excerpts, and artifact-link context to
the context pipeline. Provider-neutral; no SDK types leak into the domain
layer.

Canonical references:
    - ADR 0001 (provider-neutral boundary)
    - ADR 0003 (memory vs knowledge — context is neither)
    - ADR 0011 (harness boundaries)
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ContextProvider(Protocol):
    """Protocol for providers that inject context into prompt envelopes."""

    async def provide(self, session_id: str, user_input: str) -> str:
        """Return context text to prepend to a prompt envelope.

        Args:
            session_id: The current session identifier.
            user_input: The user message being answered.

        Returns:
            A string of context metadata to inject into the system prompt.
        """


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContextFragment:
    """A single block of context text with metadata."""

    heading: str
    content: str

    def render(self) -> str:
        """Render this fragment in a human-readable format."""
        return f"## {self.heading}\n{self.content}"


# ---------------------------------------------------------------------------
# Secret-scrubbing
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:api[_-]?key|token|secret|password)\s*[=:]\s*\S+", re.I),
    re.compile(r"-----BEGIN\s+(?:RSA|EC|DSA)\s+PRIVATE\s+KEY-----", re.I),
    re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}", re.I),
)


def scrub_secrets(text: str) -> str:
    """Redact likely secrets from context text.

    Args:
        text: Raw context text that may contain sensitive values.

    Returns:
        Text with secret patterns replaced by ``[REDACTED]``.
    """
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


# ---------------------------------------------------------------------------
# Path-safety
# ---------------------------------------------------------------------------


def _is_safe_path(repo_root: Path, path: Path) -> bool:
    """Check that *path* resolves inside *repo_root* (no symlinks escaping)."""
    try:
        return path.resolve().is_relative_to(repo_root.resolve())
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------

DEFAULT_MAX_FILE_SIZE = 8192  # bytes — truncate files beyond this size


class RepoContextProvider:
    """Provider that feeds git + filesystem + artifact context into prompts.

    Args:
        repo_root: The repository root path.
        max_file_size: Maximum bytes per file excerpt (default 8192).
    """

    def __init__(
        self,
        repo_root: Path | str,
        *,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    ) -> None:
        self._repo_root = Path(repo_root).resolve()
        self._max_file_size = max_file_size

    @property
    def repo_root(self) -> Path:
        """Read-only access to the repository root."""
        return self._repo_root

    # ---- public API ----------------------------------------------------

    async def provide(self, session_id: str, user_input: str) -> str:
        """Assemble context fragments for the given session and input.

        Returns a single string containing all context sections, each
        prefixed by a heading.
        """
        fragments: list[ContextFragment] = []

        try:
            fragments.append(self._git_status_fragment())
        except subprocess.CalledProcessError:
            pass  # Not a git repo — skip git section.
        except OSError:
            pass  # Permissions issue — skip.

        fragments.append(self._filesystem_excerpts_fragment())
        fragments.append(self._artifact_references_fragment(session_id))

        rendered = "\n\n".join(f.render() for f in fragments)
        return scrub_secrets(rendered)

    # ---- fragment builders ---------------------------------------------

    def _git_status_fragment(self) -> ContextFragment:
        """Capture git status, branch, and uncommitted changes."""
        lines: list[str] = []

        # Branch
        try:
            branch = subprocess.check_output(
                ["git", "-C", str(self._repo_root), "branch", "--show-current"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            lines.append(f"branch: {branch or '(detached)'}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            lines.append("branch: (detached or not a git repo)")

        # Status
        try:
            status = subprocess.check_output(
                ["git", "-C", str(self._repo_root), "status", "--porcelain"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if status:
                lines.extend(status.splitlines())
            else:
                lines.append("working tree: clean")
        except (subprocess.CalledProcessError, FileNotFoundError):
            lines.append("working tree: (unable to read)")

        return ContextFragment(
            heading="Git context",
            content="\n".join(lines),
        )

    def _filesystem_excerpts_fragment(self) -> ContextFragment:
        """List relevant files and include short excerpts."""
        lines: list[str] = []

        try:
            tracked_files = (
                subprocess.check_output(
                    ["git", "-C", str(self._repo_root), "ls-files"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
                .strip()
                .splitlines()
            )

            # Only show first 20 tracked files to avoid dump.
            for rel_path in tracked_files[:20]:
                file_path = self._repo_root / rel_path
                if not file_path.is_file():
                    continue
                if not _is_safe_path(self._repo_root, file_path):
                    continue
                content = self._read_file_excerpt(file_path)
                lines.append(f"- {rel_path} ({len(content)} bytes)")
        except (subprocess.CalledProcessError, FileNotFoundError):
            lines.append("(no tracked files)")

        return ContextFragment(
            heading="Relevant files",
            content="\n".join(lines) or "(none)",
        )

    def _artifact_references_fragment(self, session_id: str) -> ContextFragment:
        """Reference any known artifacts for this session."""
        lines: list[str] = [f"session: {session_id}"]

        # List any artifact-like directories (plans, diffs, check results)
        for subdir in ("plans", "artifacts", "checks"):
            dir_path = self._repo_root / subdir
            if dir_path.is_dir():
                child_files = sorted(dir_path.iterdir())
                for child in child_files[:10]:
                    lines.append(f"artifact: {subdir}/{child.name}")

        return ContextFragment(
            heading="Artifact references",
            content="\n".join(lines),
        )

    def _read_file_excerpt(self, file_path: Path) -> str:
        """Read up to ``max_file_size`` bytes from *file_path*."""
        if not file_path.is_file():
            return "(file not found)"
        if not _is_safe_path(self._repo_root, file_path):
            return "(access denied)"
        try:
            data = file_path.read_bytes()
            if len(data) > self._max_file_size:
                truncated = data[: self._max_file_size]
                return truncated.decode("utf-8", errors="replace") + (
                    "\n... [truncated, exceeded max file size]"
                )
            return data.decode("utf-8", errors="replace")
        except OSError:
            return "(unable to read)"
