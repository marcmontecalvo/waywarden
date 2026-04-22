"""Static import-scan: domain must not import sqlalchemy."""

import ast
from pathlib import Path


def test_no_sqlalchemy_in_domain() -> None:
    """No file under src/waywarden/domain/ imports sqlalchemy."""
    domain_root = Path(__file__).parents[3] / "waywarden" / "domain"
    for py in domain_root.rglob("*.py"):
        src = py.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "sqlalchemy" in node.module:
                raise AssertionError(
                    f"{py.relative_to(domain_root.parent)} imports sqlalchemy ({node.module})"
                )
