"""Filesystem knowledge provider.

Reads markdown files from a configured root directory, indexes them by title
and body content, and serves search + fetch operations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from waywarden.domain.providers.types.knowledge import (
    KnowledgeDocument,
    KnowledgeHit,
)


class KnowledgeNotFound(ValueError):
    """Raised when a knowledge document cannot be found."""


@dataclass(frozen=True)
class _IndexedDoc:
    """Internal index entry for a knowledge document."""

    ref: str
    title: str
    body: str
    path: Path


def _extract_yaml_frontmatter(title: str, raw: str) -> tuple[str, str]:
    """Return (title_override, content_without_frontmatter)."""
    yaml_block_re = re.compile(r"^---\s*\n(.*?\n)?---\s*\n", re.DOTALL)
    match = yaml_block_re.match(raw)
    if match:
        content = raw[match.end() :]
        yaml_text = match.group(0)
        # Simple frontmatter title extraction
        title_match = re.search(r"^title:\s*(.+)$", yaml_text, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip().strip('"').strip("'")
        return title, content
    return title, raw


def _parse_title_from_path(path: Path) -> str:
    """Best-effort human-readable title from a filepath."""
    stem = path.stem
    return stem.replace("-", " ").replace("_", " ").title()


class FilesystemKnowledgeProvider:
    """KnowledgeProvider backed by a local directory of markdown files."""

    def __init__(self, root: Path) -> None:
        if not root.is_dir():
            raise NotADirectoryError(f"knowledge root is not a directory: {root}")
        self._root = root.resolve()
        self._docs: list[_IndexedDoc] = []
        self._build_index()

    def _build_index(self) -> None:
        self._docs = []
        for md_file in sorted(self._root.rglob("*.md")):
            raw = md_file.read_text(encoding="utf-8")
            title = _parse_title_from_path(md_file)
            title, body = _extract_yaml_frontmatter(title, raw)
            # Strip frontmatter headings for body
            body = re.sub(r"^#+\s+.+$\n?", "", body, flags=re.MULTILINE).strip()
            # Deduplicate empty bodies
            if not body:
                body = raw
            ref = str(md_file.relative_to(self._root))
            self._docs.append(
                _IndexedDoc(
                    ref=ref,
                    title=title,
                    body=body,
                    path=md_file,
                )
            )

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[KnowledgeHit]:
        query_lower = query.lower()
        hits: list[tuple[str, str, float, str]] = []  # (ref, title, score, snippet)

        for doc in self._docs:
            title_match = query_lower in doc.title.lower()
            body_match = query_lower in doc.body.lower()
            if not title_match and not body_match:
                continue

            score = 2.0 if title_match else 1.0
            if body_match and not title_match:
                snippet = _build_snippet(doc.body, query, window=60)
            elif title_match:
                snippet = f"{doc.title}: {_snippet_from(doc.body, query, 40)}"
            else:
                snippet = _snippet_from(doc.body, query, 80)

            # Sort key: alphabetical by ref (deterministic for ties)
            hits.append((doc.ref, doc.title, float(score), snippet))

        # Sort by score descending, then alphabetical by path (ref) for ties
        hits.sort(key=lambda h: (-h[2], h[0]))

        return [KnowledgeHit(ref=h[0], title=h[1], snippet=h[3], score=h[2]) for h in hits[:limit]]

    async def fetch(self, ref: str) -> KnowledgeDocument:
        for doc in self._docs:
            if doc.ref == ref:
                return KnowledgeDocument(
                    ref=doc.ref,
                    title=doc.title,
                    content=doc.body,
                )
        raise KnowledgeNotFound(f"knowledge document not found: {ref}")


def _snippet_from(text: str, query: str, max_len: int = 80) -> str:
    """Extract a snippet around the first query match."""
    query_lower = query.lower()
    idx = text.lower().find(query_lower)
    if idx == -1:
        return text[:max_len]
    start = max(0, idx - 20)
    end = min(len(text), idx + len(query) + 40)
    snippet = text[start:end].strip()
    return snippet


def _build_snippet(body: str, query: str, window: int = 60) -> str:
    """Build a result snippet around the first match."""
    query_lower = query.lower()
    idx = body.lower().find(query_lower)
    if idx == -1:
        return body[:window]
    start = max(0, idx - 10)
    end = min(len(body), idx + len(query) + window)
    snippet = body[start:end].strip()
    return snippet
