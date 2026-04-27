"""Tests for the repo-aware context provider (P6-2 #93)."""

import subprocess
from pathlib import Path

import pytest

from waywarden.domain.context_provider import (
    ContextFragment,
    RepoContextProvider,
    _is_safe_path,
    scrub_secrets,
)

FIXTURES_DIR = Path("tests/fixtures").resolve()
SAMPLE_REPO_DIR = Path("tests/fixtures/sample_repo").resolve()


# -----------------------------------------------------------------------
# ContextFragment rendering
# -----------------------------------------------------------------------


def test_fragment_render() -> None:
    f = ContextFragment(heading="Git", content="branch: main")
    assert f.render() == "## Git\nbranch: main"


# -----------------------------------------------------------------------
# Secret scrubbing
# -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("api_key: abc123", "[REDACTED]"),
        ("token = xyz789", "[REDACTED]"),
        ("secret: mysecret", "[REDACTED]"),
        ("password: hunter2", "[REDACTED]"),
        ("no secrets here", "no secrets here"),
        (
            "-----BEGIN RSA PRIVATE KEY-----",
            "[REDACTED]",
        ),
        (
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
            "[REDACTED]",
        ),
    ],
)
def test_scrub_secrets(text: str, expected: str) -> None:
    assert scrub_secrets(text) == expected


# -----------------------------------------------------------------------
# Path-safety
# -----------------------------------------------------------------------


def test_is_safe_path_inside_repo() -> None:
    root = Path("/tmp/repo")
    child = Path("/tmp/repo/src/file.txt")
    assert _is_safe_path(root, child)


def test_is_safe_path_sibling_outside() -> None:
    root = Path("/tmp/repo")
    sibling = Path("/tmp/other/file.txt")
    assert not _is_safe_path(root, sibling)


def test_is_safe_path_parent_escape() -> None:
    root = Path("/tmp/repo")
    escape = Path("/tmp/repo/../other/file.txt")
    assert not _is_safe_path(root, escape)


# -----------------------------------------------------------------------
# RepoContextProvider — clean repo
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provide_context_clean_git_repo(tmp_path: Path) -> None:
    """Provide context in a clean git repo returns git + files + artifacts sections."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Test repo", encoding="utf-8")

    subprocess.run(
        ["git", "init", str(repo)],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@test.com"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "add", "."],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"],
        capture_output=True,
        check=True,
    )

    ctx = RepoContextProvider(repo)
    result = await ctx.provide("test-session", "hello")

    assert "Git context" in result
    assert "Relevant files" in result
    assert "Artifact references" in result
    assert "README.md" in result


# -----------------------------------------------------------------------
# RepoContextProvider — dirty worktree
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provide_context_dirty_worktree(tmp_path: Path) -> None:
    """Uncommitted changes appear in git status output."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Test repo", encoding="utf-8")

    subprocess.run(
        ["git", "init", str(repo)],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@test.com"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "add", "."],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"],
        capture_output=True,
        check=True,
    )

    # Commit change so we can add untracked file
    (repo / "CHANGELOG.md").write_text("v1.0.0", encoding="utf-8")

    ctx = RepoContextProvider(repo)
    result = await ctx.provide("test-session", "hello")

    # Untracked file should appear
    assert "Relevant files" in result
    assert "CHANGELOG.md" in result or "CHANGELOG" in result


# -----------------------------------------------------------------------
# RepoContextProvider — missing file handling
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provide_context_missing_file_safe() -> None:
    """Provider does not crash when a tracked file is missing."""
    ctx = RepoContextProvider("/tmp/nonexistent-repo")
    result = await ctx.provide("test-session", "hello")
    # Should not raise; should gracefully handle missing path
    assert isinstance(result, str)
    assert len(result) > 0


# -----------------------------------------------------------------------
# RepoContextProvider — large file truncation
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_file_excerpt_truncation(tmp_path: Path) -> None:
    """Large files are truncated at max_file_size."""
    repo = tmp_path / "repo"
    repo.mkdir()
    large_file = repo / "big.txt"
    large_file.write_bytes(b"A" * 20000)

    ctx = RepoContextProvider(repo, max_file_size=8192)
    excerpt = ctx._read_file_excerpt(large_file)
    assert "... [truncated" in excerpt
    # The content before the truncation message should be at most max_file_size + 1 (newline)
    content_part = excerpt.split("\n... [truncated")[0]
    assert len(content_part) == 8192


# -----------------------------------------------------------------------
# RepoContextProvider — non-git repo
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provide_context_non_git_repo(tmp_path: Path) -> None:
    """A non-git directory still returns context sections."""
    repo = tmp_path / "no-git"
    repo.mkdir()
    (repo / "README.md").write_text("# No git", encoding="utf-8")

    ctx = RepoContextProvider(repo)
    result = await ctx.provide("test-session", "hello")

    # Should not crash
    assert isinstance(result, str)
    assert len(result) > 0


# -----------------------------------------------------------------------
# RepoContextProvider — scrubbing in provide output
# -----------------------------------------------------------------------


def test_scrub_secrets_removes_github_tokens() -> None:
    """GitHub personal access tokens are redacted."""
    text = "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcd1234"
    assert "ghp_" not in scrub_secrets(text)
    assert "[REDACTED]" in scrub_secrets(text)


def test_scrub_secrets_preserves_normal_paths() -> None:
    """Normal file paths are preserved."""
    text = "src/waywarden/domain/context_provider.py"
    assert scrub_secrets(text) == text


# -----------------------------------------------------------------------
# RepoContextProvider — repo_root property
# -----------------------------------------------------------------------


def test_repo_root_property_resolves() -> None:
    ctx = RepoContextProvider("/tmp/test")
    assert ctx.repo_root == Path("/tmp/test").resolve()


# -----------------------------------------------------------------------
# Artifact references section
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_artifact_references_lists_subdir_contents(tmp_path: Path) -> None:
    """Artifact references include contents of plans/ artifacts/ directories."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "plans").mkdir()
    (repo / "plans" / "plan1.md").write_text("plan", encoding="utf-8")
    (repo / "artifacts").mkdir()
    (repo / "artifacts" / "diff1.patch").write_text("diff", encoding="utf-8")

    ctx = RepoContextProvider(repo)
    result = await ctx.provide("test-session", "hello")

    assert "plans/plan1.md" in result
    assert "artifacts/diff1.patch" in result


# -----------------------------------------------------------------------
# Path safety — symlink escape
# -----------------------------------------------------------------------


def test_is_safe_path_symlink_escape(tmp_path: Path) -> None:
    """A symlink escaping the repo root is rejected."""
    repo = tmp_path / "repo"
    repo.mkdir()
    escape = tmp_path / "outside"
    escape.mkdir()
    (escape / "file.txt").write_text("xxx", encoding="utf-8")

    # Create a symlink inside repo pointing outside
    link = repo / "link"
    link.symlink_to(escape)
    link_file = link / "file.txt"

    # The symlink target resolves outside — should be unsafe
    assert not _is_safe_path(repo, link_file)
