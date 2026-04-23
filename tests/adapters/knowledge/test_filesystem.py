"""Tests for the filesystem knowledge provider."""

from __future__ import annotations

from pathlib import Path

import pytest

from waywarden.adapters.knowledge.filesystem import (
    FilesystemKnowledgeProvider,
    KnowledgeNotFound,
)
from waywarden.domain.providers.types.knowledge import KnowledgeDocument, KnowledgeHit

_TEST_KNOWLEDGE_DIR = Path(__file__).parent / "_knowledge_fixtures"


@pytest.fixture(autouse=True)
def knowledge_fixture_dir(tmp_path: Path) -> Path:
    """Create a fixture directory with sample markdown files."""
    kdir = tmp_path / "knowledge"
    kdir.mkdir()

    # File 1: Title match
    (kdir / "getting-started.md").write_text(
        "---\ntitle: Getting Started\n---\n\nThis is the getting started guide.\n\n"
        "Install waywarden with uv to begin.",
        encoding="utf-8",
    )

    # File 2: Body match only
    (kdir / "advanced-reference.md").write_text(
        "---\ntitle: Advanced Reference\n---\n\n"
        "This file contains advanced configuration.\n"
        "The quick brown fox jumps over the fence.\n",
        encoding="utf-8",
    )

    # File 3: No match
    (kdir / "changelog.md").write_text(
        "# Changelog\n\nv1.0.0 - initial release.\n",
        encoding="utf-8",
    )

    # Subdirectory
    sub = kdir / "sub"
    sub.mkdir()
    (sub / "deep-doc.md").write_text(
        "---\ntitle: Deep Doc\n---\n\n"
        "This document lives deep and mentions the fox as well.\n",
        encoding="utf-8",
    )

    return kdir


async def test_search_matches_titles_and_bodies(
    knowledge_fixture_dir: Path,
) -> None:
    """FilesystemKnowledgeProvider.search("term") matches titles and body
    substrings; returns deterministic KnowledgeHit order (alphabetical by path
    for ties)."""
    provider = FilesystemKnowledgeProvider(root=knowledge_fixture_dir)

    # Search for "getting" should match the title of getting-started.md
    results = await provider.search("getting")
    assert len(results) == 1
    assert isinstance(results[0], KnowledgeHit)
    assert results[0].ref == "getting-started.md"
    assert results[0].score == 2.0  # title match = higher score
    assert "getting started" in results[0].title.lower()

    # Search for "fox" should only match body of advanced-reference.md
    # and deep-doc.md
    results_fox = await provider.search("fox")
    assert len(results_fox) == 2

    # Both have score 1.0 (body only), so ties broken alphabetically by path
    assert results_fox[0].ref == "advanced-reference.md"
    assert results_fox[1].ref == "sub/deep-doc.md"

    # Search for "v1" should only match changelog.md
    results_v1 = await provider.search("v1")
    assert len(results_v1) == 1
    assert results_v1[0].ref == "changelog.md"

    # Search for non-existent term returns empty
    results_empty = await provider.search("zxcvbn")
    assert results_empty == []


async def test_fetch_missing_raises(knowledge_fixture_dir: Path) -> None:
    """FilesystemKnowledgeProvider.fetch(ref) reads the referenced file;
    invalid ref raises KnowledgeNotFound."""
    provider = FilesystemKnowledgeProvider(root=knowledge_fixture_dir)

    # Valid fetch
    doc = await provider.fetch("getting-started.md")
    assert isinstance(doc, KnowledgeDocument)
    assert doc.title == "Getting Started"
    assert "Install waywarden" in doc.content
    assert doc.ref == "getting-started.md"

    # Subdirectory fetch
    sub_doc = await provider.fetch("sub/deep-doc.md")
    assert isinstance(sub_doc, KnowledgeDocument)
    assert sub_doc.title == "Deep Doc"
    assert "lives deep" in sub_doc.content

    # Invalid ref raises KnowledgeNotFound
    with pytest.raises(KnowledgeNotFound, match="fake-file.md"):
        await provider.fetch("fake-file.md")

    # Another invalid ref
    with pytest.raises(KnowledgeNotFound, match="nonexistent.md"):
        await provider.fetch("nonexistent.md")
