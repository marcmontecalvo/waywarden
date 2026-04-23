"""YAML loader for policy presets.

Resolves a preset name plus optional overrides into a domain
:class:`~waywarden.domain.manifest.tool_policy.ToolPolicy`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from waywarden.domain.manifest.tool_policy import (
    ToolDecisionRule as DomainToolDecisionRule,
)
from waywarden.domain.manifest.tool_policy import (
    ToolPolicy as DomainToolPolicy,
)
from waywarden.policy.schema import PolicyPresetDoc, ToolDecisionRule as SchemaRule
from typing import Any

# Default preset directory — overridden for testing.
_PRESETS_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "policy" / "presets"


class PolicyLoaderError(Exception):
    """Base error for policy-loading failures."""

    pass


class UnknownPresetError(PolicyLoaderError):
    """The requested preset name has no matching YAML file."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Unknown preset: {name}")
        self.name = name


@dataclass(frozen=True)
class PolicyLoader:
    """Stateless loader for policy-preset YAML files."""

    presets_dir: Path | None = None

    # --- public API ---------------------------------------------------------------

    def load(
        self,
        name: str,
        *,
        override: Mapping[str, object] | None = None,
    ) -> DomainToolPolicy:
        """Load a preset by name, merge overrides, return a domain ``ToolPolicy``.

        Parameters
        ----------
        name:
            Preset name (must correspond to ``<name>.yaml`` in the presets directory).
        override:
            Optional dict of overrides to merge into the base preset.

        Returns
        -------
        :
            A frozen ``ToolPolicy`` ready for use in the workspace manifest.

        Raises
        ------
        UnknownPresetError
            When no ``{name}.yaml`` file exists.
        PolicyLoaderError
            When the YAML content is malformed or fails schema validation.
        """
        presets_dir = self.presets_dir or _PRESETS_DIR
        preset_path = presets_dir / f"{name}.yaml"

        if not preset_path.is_file():
            json_path = presets_dir / f"{name}.json"
            if json_path.is_file():
                preset_path = json_path
            else:
                raise UnknownPresetError(name)

        raw = self._read_yaml(preset_path)
        doc = self._validate(raw)
        merged = self._merge_overrides(doc, override)
        return self._to_domain(merged)

    # --- internal helpers ---------------------------------------------------------

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        """Return parsed YAML content."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise PolicyLoaderError(f"Cannot read {path}: {exc}") from exc
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise PolicyLoaderError(f"Malformed YAML in {path}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise PolicyLoaderError(
                f"Expected a YAML mapping in {path}, got {type(parsed).__name__}"
            )
        return parsed

    @staticmethod
    def _validate(raw: dict) -> PolicyPresetDoc:
        """Validate YAML dict against the pydantic schema."""
        try:
            return PolicyPresetDoc.model_validate(raw)
        except Exception as exc:
            raise PolicyLoaderError(
                f"Schema validation failed for preset: {exc}"
            ) from exc

    @staticmethod
    def _merge_overrides(
        doc: PolicyPresetDoc,
        override: Mapping[str, object] | None,
    ) -> PolicyPresetDoc:
        """Apply override values, merging at the rules level.

        Override precedence: an override rule for the same ``tool`` name
        replaces the base rule entirely.
        """
        if not override:
            return doc

        rules = list(doc.rules)
        overrides_raw = override.get("rules", [])
        if not isinstance(overrides_raw, list):
            return doc

        override_map: dict[str, SchemaRule] = {}
        for ov in overrides_raw:
            if not isinstance(ov, dict):
                continue
            try:
                rule = SchemaRule.model_validate(ov)
            except Exception:
                continue
            override_map[rule.tool] = rule

        existing: set[str] = set()
        merged_rules: list[SchemaRule] = []
        for rule in rules:
            if rule.tool in override_map:
                merged_rules.append(override_map[rule.tool])
                existing.add(rule.tool)
            else:
                merged_rules.append(rule)
                existing.add(rule.tool)

        for tool_name, rule in override_map.items():
            if tool_name not in existing:
                merged_rules.append(rule)

        return doc.model_copy(update={"rules": merged_rules})

    @staticmethod
    def _to_domain(doc: PolicyPresetDoc) -> DomainToolPolicy:
        """Convert a validated schema document into the domain ``ToolPolicy``."""
        domain_rules: list[DomainToolDecisionRule] = [
            DomainToolDecisionRule(
                tool=r.tool,
                action=r.action,
                decision=r.decision,
                reason=r.reason,
            )
            for r in doc.rules
        ]
        return DomainToolPolicy(
            preset=doc.preset,
            default_decision=doc.default_decision,
            rules=domain_rules,
        )
