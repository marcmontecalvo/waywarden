"""YAML loader for policy presets.

Resolves a preset name plus optional overrides into a domain
:class:`~waywarden.domain.manifest.tool_policy.ToolPolicy`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from waywarden.domain.manifest.tool_policy import (
    ToolDecisionRule as DomainToolDecisionRule,
)
from waywarden.domain.manifest.tool_policy import (
    ToolPolicy as DomainToolPolicy,
)
from waywarden.policy.schema import PolicyPresetDoc
from waywarden.policy.schema import ToolDecisionRule as SchemaRule

# Default preset directory — overridden for testing.
# parents[0]=policy, [1]=waywarden, [2]=src, [3]=repo root.
_PRESETS_DIR: Path = Path(__file__).resolve().parents[3] / "config" / "policy" / "presets"


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

    def list_presets(self) -> list[str]:
        """Return sorted list of preset names discoverable in the presets directory.

        Returns filenames (without extension) for every ``.yaml`` file
        in the configured presets directory.
        """
        presets_dir = self.presets_dir or _PRESETS_DIR
        if not presets_dir.is_dir():
            return []
        return sorted(p.stem for p in presets_dir.glob("*.yaml"))

    def load(
        self,
        name: str,
        *,
        override: Mapping[str, Any] | None = None,
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
        override: Mapping[str, Any] | None,
    ) -> PolicyPresetDoc:
        """Apply override values, merging at the rules level.

        Override precedence: an override rule for the same ``tool`` name
        replaces the base rule entirely.

        Also supports overriding ``default_decision`` directly at the top level.
        """
        if not override:
            return doc

        merged_rules = list(doc.rules)

        # Handle rules overrides
        overrides_raw = override.get("rules", [])
        if isinstance(overrides_raw, list):
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
            for rule in merged_rules:
                if rule.tool in override_map:
                    merged_rules[merged_rules.index(rule)] = override_map[rule.tool]
                    existing.add(rule.tool)
                else:
                    existing.add(rule.tool)

            for tool_name, rule in override_map.items():
                if tool_name not in existing:
                    merged_rules.append(rule)

        if "default_decision" in override:
            return doc.model_copy(
                update={"rules": merged_rules, "default_decision": override["default_decision"]}
            )
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
