"""Unit import-scan: repository Protocols must not import sqlalchemy."""

import ast
from pathlib import Path


def test_protocols_have_no_sqlalchemy_import() -> None:
    """No file under src/waywarden/domain/repositories/ imports sqlalchemy."""
    domain_root = Path(__file__).parents[3] / "waywarden" / "domain" / "repositories"
    for py in domain_root.rglob("*.py"):
        if py.name == "__init__.py" and "repositories" in py.parts:
            # Skip the __init__.py that re-exports — it imports from protocols.py
            continue
        src = py.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "sqlalchemy" in node.module:
                raise AssertionError(
                    f"{py.relative_to(domain_root.parent)} imports sqlalchemy ({node.module})"
                )
