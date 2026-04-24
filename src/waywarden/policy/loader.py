<<<<<<< HEAD
"""YAML loader for policy presets.

Resolves a preset name plus optional overrides into a domain
:class:`~waywarden.domain.manifest.tool_policy.ToolPolicy`.
=======
"""PolicyLoader — reads preset YAML and produces domain ``ToolPolicy``.

Resolves a preset name from ``config/policy/presets/{name}.yaml``,
optionally merges overrides, and returns a domain ``ToolPolicy``
suitable for attachment to a ``WorkspaceManifest``.
>>>>>>> 7c5089dabbd83f11c39650e78b76e58c185e571e
"""

from __future__ import annotations

<<<<<<< HEAD
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
=======
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import yaml

from waywarden.domain.manifest.tool_policy import ToolPolicy
from waywarden.policy.schema import PolicyPresetDoc


class PolicyLoaderError(RuntimeError):
    """General policy loading failure (malformed YAML, etc.)."""


class UnknownPresetError(PolicyLoaderError):
    """Requested preset does not exist."""


class PolicyLoader:
    """Load policy presets from YAML files.

    Parameters
    ----------
    presets_dir:
        Directory that contains ``{preset_name}.yaml`` files.
    """

    def __init__(self, presets_dir: Path | None = None) -> None:
        if presets_dir is None:
            presets_dir = Path("config/policy/presets")
        self.presets_dir = presets_dir

    def list_presets(self) -> list[str]:
        """Return sorted names of all available preset files."""
        if not self.presets_dir.is_dir():
            return []
        names: list[str] = []
        for file in sorted(self.presets_dir.iterdir()):
            if file.suffix in (".yaml", ".yml"):
                names.append(file.stem)
        return names
>>>>>>> 7c5089dabbd83f11c39650e78b76e58c185e571e

    def load(
        self,
        name: str,
        *,
<<<<<<< HEAD
        override: Mapping[str, object] | None = None,
    ) -> DomainToolPolicy:
        """Load a preset by name, merge overrides, return a domain ``ToolPolicy``.
=======
        override: Mapping[str, Any] | None = None,
    ) -> ToolPolicy:
        """Load a preset by ``name`` and produce a domain ``ToolPolicy``.
>>>>>>> 7c5089dabbd83f11c39650e78b76e58c185e571e

        Parameters
        ----------
        name:
<<<<<<< HEAD
            Preset name (must correspond to ``<name>.yaml`` in the presets directory).
        override:
            Optional dict of overrides to merge into the base preset.

        Returns
        -------
        :
            A frozen ``ToolPolicy`` ready for use in the workspace manifest.
=======
            Preset file stem (e.g. ``"ask"``).
        override:
            Optional dictionary of keys to merge on top of the loaded
            ``PolicyPresetDoc`` before converting to domain.

        Returns
        -------
        ToolPolicy
            The resolved domain policy.
>>>>>>> 7c5089dabbd83f11c39650e78b76e58c185e571e

        Raises
        ------
        UnknownPresetError
<<<<<<< HEAD
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
=======
            When the preset file does not exist.
        PolicyLoaderError
            On malformed YAML or validation failure.
        """
        preset_path = self.presets_dir / f"{name}.yaml"
        if not preset_path.is_file():
            raise UnknownPresetError(f"Unknown preset '{name}'; expected {preset_path}")

        try:
            raw = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise PolicyLoaderError(f"Malformed YAML in {preset_path}: {exc}") from exc

        if not isinstance(raw, dict):
            raise PolicyLoaderError(
                f"Preset {preset_path} did not resolve to a mapping; got {type(raw).__name__}"
            )

        doc: PolicyPresetDoc
        try:
            doc = PolicyPresetDoc(**raw)
        except Exception as exc:
            raise PolicyLoaderError(
                f"Validation failed for preset '{name}' in {preset_path}: {exc}"
            ) from exc

        if override is not None:
            doc = self._apply_overrides(doc, override)

        return doc.to_domain()

    @staticmethod
    def _apply_overrides(
        doc: PolicyPresetDoc,
        override: Mapping[str, Any],
    ) -> PolicyPresetDoc:
        """Merge ``override`` keys into ``doc`` fields.

        Only ``default_decision`` and ``rules`` are supported override
        targets.  Any other key is silently ignored (future-proofing).
        """
        merged: dict[str, Any] = doc.model_dump(mode="json")

        if "default_decision" in override:
            merged["default_decision"] = override["default_decision"]

        if "rules" in override:
            existing_rules: list[dict[str, Any]] = list(merged.get("rules", []))
            raw_override_rules: list[dict[str, Any]] = list(override["rules"])
            rule_map: dict[tuple[str, str | None], dict[str, Any]] = {}
            for r in existing_rules:
                key: tuple[str, str | None] = (r["tool"], r.get("action"))
                rule_map[key] = r
            for r in raw_override_rules:
                key = (r["tool"], r.get("action"))
                rule_map[key] = r
            merged["rules"] = list(rule_map.values())

        return PolicyPresetDoc(**merged)
>>>>>>> 7c5089dabbd83f11c39650e78b76e58c185e571e
