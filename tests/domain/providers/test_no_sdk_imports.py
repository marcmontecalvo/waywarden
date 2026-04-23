"""Static scan to ensure domain/providers/ imports no provider SDKs."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path


def _get_provider_package_root() -> Path:
    domain_providers = importlib.import_module("waywarden.domain.providers")
    return Path(domain_providers.__file__).parent


_SDK_PACKAGES = ("openai", "anthropic", "httpx", "langchain", "litellm")


def _scan_file(filepath: Path) -> list[str]:
    """Return list of top-level imports found in *filepath*."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filepath.name)
    except (OSError, SyntaxError):
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and not node.module.startswith(
            "waywarden"
        ):
            imports.append(node.module.split(".")[0])
    return imports


def test_domain_has_no_sdk_imports() -> None:
    """No file under src/waywarden/domain/providers/ may import a provider SDK."""
    root = _get_provider_package_root()
    found_violations: list[str] = []

    for modname in _collect_module_names(root):
        filepath = root / (modname.replace(".", "/") + ".py")
        if not filepath.exists():
            continue
        imports = _scan_file(filepath)
        for imp in imports:
            if imp in _SDK_PACKAGES:
                found_violations.append(f"{filepath.name}: imports {imp}")

    assert not found_violations, (
        "Provider domain files must not import provider SDKs:\n"
        + "\n".join(found_violations)
    )


def _collect_module_names(root: Path) -> list[str]:
    """Walk the package directory and return .py module names relative to root."""
    names: list[str] = []
    for filepath in root.rglob("*.py"):
        if filepath.name == "__init__.py":
            rel = filepath.relative_to(root)
            parts = list(rel.parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            if parts:
                names.append(".".join(parts))
        else:
            rel = filepath.relative_to(root)
            parts = list(rel.parts)
            parts[-1] = parts[-1][:-3]  # strip .py
            names.append(".".join(parts))
    return names
