"""Static import isolation test: memory adapters must not import knowledge adapters."""

from __future__ import annotations

import importlib
import sys


def test_no_cross_imports() -> None:
    """Ensure no `adapters/memory/*` core file imports anything from `adapters/knowledge/*`."""
    memory_modules = ["waywarden.adapters.memory.fake", "waywarden.adapters.memory.honcho"]
    knowledge_modules = ["waywarden.adapters.knowledge"]

    for mod_name in memory_modules:
        mod = importlib.import_module(mod_name)
        source_file = getattr(mod, "__file__", None)
        if source_file is None or not source_file.endswith(".py"):
            continue

        with open(source_file, encoding="utf-8") as f:
            source = f.read()

        for km in knowledge_modules:
            assert km not in source, f"{source_file} contains a reference to {km}"
