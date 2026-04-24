"""ADR-0003 boundary test — no merged context block allowed.

ADR-0003 requires memory and knowledge to stay separate.  This test
scans the context builder source for any shared ``context_block`` container
that would indicate a drift from the ADR.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent  # repo root
SRC = ROOT / "src"


def _read_context_builder_source() -> str:
    """Return the content of context_builder.py."""
    path = SRC / "waywarden" / "services" / "context_builder.py"
    return path.read_text(encoding="utf-8")


def test_no_merged_block_type() -> None:
    """Greps the source for any shared context_block container.

    If a unified context_block type is introduced, the ADR-0003 spec
    must be updated first.  This test prevents accidental fusion.
    """
    source = _read_context_builder_source()

    # Look for patterns indicating a merged block:
    # - class/struct named context_block
    # - field named context_block
    #
    # We allow `context_memory_char_cap` and `context_knowledge_char_cap`
    # to exist.
    merged_patterns = [
        r"\bcontext_block\b",
        r"context_block\s*:",
    ]

    for pattern in merged_patterns:
        matches = re.findall(pattern, source)
        # Filter out the valid config fields
        for match in matches:
            # context_memory_char_cap and context_knowledge_char_cap are fine
            stripped = match.strip()
            if "context_memory_char_cap" in stripped or "context_knowledge_char_cap" in stripped:
                continue
            pytest.fail(
                f"ADR-0003 violation: found '{stripped}' in context_builder.py. "
                f"Memory and knowledge must stay as separate blocks. "
                f"Update ADR-0003 before introducing unified containers."
            )


def test_envelope_has_separate_fields() -> None:
    """PromptEnvelope must have distinct memory_block and knowledge_block fields."""
    import importlib


    module = importlib.import_module("waywarden.domain.providers.types.model")
    source = module.__file__
    if source is None:
        pytest.skip("cannot locate model.py source")

    source_text = pathlib.Path(source).read_text(encoding="utf-8")

    # Verify the fields exist as distinct typed attributes
    assert "memory_block" in source_text, "PromptEnvelope must have memory_block field"
    assert "knowledge_block" in source_text, "PromptEnvelope must have knowledge_block field"

    # They should reference distinct types
    assert "MemoryEntry" in source_text
    assert "KnowledgeHit" in source_text
